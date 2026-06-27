from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session
from database.database import get_session
from models.user import User
from models.forecast import Forecast, TaskStatus
from services.crud.forecast import (
    get_forecast_by_id,
    get_forecasts_by_user,
    get_forecast_items
)
from collections import defaultdict
import numpy as np
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ml_worker'))
from forecaster import run_forecast as run_forecast_model

from services.forecast import create_forecast_task
from dependencies.auth import get_current_user_universal
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import logging
import io
import csv
import json
from typing import Union

logger = logging.getLogger(__name__)

forecast_router = APIRouter(prefix="/api/forecast", tags=["Forecast"])


class ForecastCreateRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: str
    store_id: Union[str, List[str]]
    dept_ids: List[str]
    horizon_days: int = 28
    alpha: float = 0.2


class ForecastResponse(BaseModel):
    forecast_id: int
    status: str
    store_id: str
    horizon_days: int
    alpha: float
    total_cost: float
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


@forecast_router.post("/run", response_model=ForecastResponse)
def run_forecast(
        request: ForecastCreateRequest,
        current_user: User = Depends(get_current_user_universal),
        session: Session = Depends(get_session)
):
    """
    Запустить задачу прогноза.
    """
    try:
        if isinstance(request.store_id, list):
            store_id_str = ",".join(request.store_id)
        else:
            store_id_str = request.store_id

        forecast = create_forecast_task(
            user_id=current_user.id,
            model_id=request.model_id,
            store_id=store_id_str,
            dept_ids=request.dept_ids,
            horizon_days=request.horizon_days,
            alpha=request.alpha,
            session=session
        )

        logger.info(f"Forecast task created: id={forecast.id}, user={current_user.email}")

        return ForecastResponse(
            forecast_id=forecast.id,
            status=forecast.status.value,
            store_id=forecast.store_id,
            horizon_days=forecast.horizon_days,
            alpha=forecast.alpha,
            total_cost=forecast.total_cost,
            created_at=forecast.created_at.isoformat(),
            completed_at=forecast.completed_at.isoformat() if forecast.completed_at else None,
            error=forecast.error
        )

    except ValueError as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        session.rollback()
        logger.error(f"Forecast creation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create forecast: {str(e)}"
        )


@forecast_router.get("/history")
def get_forecast_history(
        current_user: User = Depends(get_current_user_universal),
        session: Session = Depends(get_session)
):
    """
    Получить историю всех прогнозов пользователя.
    """
    forecasts = get_forecasts_by_user(current_user.id, session)

    return {
        "user_id": current_user.id,
        "forecasts": [
            {
                "forecast_id": f.id,
                "status": f.status.value,
                "store_id": f.store_id,
                "horizon_days": f.horizon_days,
                "alpha": f.alpha,
                "total_cost": f.total_cost,
                "created_at": f.created_at.isoformat(),
                "completed_at": f.completed_at.isoformat() if f.completed_at else None
            }
            for f in forecasts
        ]
    }


@forecast_router.get("/{forecast_id}", response_model=ForecastResponse)
def get_forecast_status(
        forecast_id: int,
        current_user: User = Depends(get_current_user_universal),
        session: Session = Depends(get_session)
):
    """
    Получить статус прогноза.
    """
    forecast = get_forecast_by_id(forecast_id, session)
    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Forecast not found"
        )

    if forecast.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return ForecastResponse(
        forecast_id=forecast.id,
        status=forecast.status.value,
        store_id=forecast.store_id,
        horizon_days=forecast.horizon_days,
        alpha=forecast.alpha,
        total_cost=forecast.total_cost,
        created_at=forecast.created_at.isoformat(),
        completed_at=forecast.completed_at.isoformat() if forecast.completed_at else None,
        error=forecast.error
    )


class SummaryItemResponse(BaseModel):
    item_id: str
    total_predicted_sales: float
    avg_daily_probability: float
    avg_daily_sales: float
    days_with_expected_sales: int
    total_days: int
    recommended_order: int
    risk_level: str
    risk_description: str


class SummaryResponse(BaseModel):
    forecast_id: int
    store_id: str
    period_start: str
    period_end: str
    horizon_days: int
    alpha: float
    total_items: int
    total_order_recommendation: int
    items: List[SummaryItemResponse]


@forecast_router.get("/{forecast_id}/summary", response_model=SummaryResponse)
def get_forecast_summary(
        forecast_id: int,
        item_id: Optional[str] = None,  # ← Параметр для фильтрации
        current_user: User = Depends(get_current_user_universal),
        session: Session = Depends(get_session)
):
    """
    Агрегированный отчёт по товарам на период.
    Возвращает рекомендации к закупке для менеджера.
    """
    forecast = get_forecast_by_id(forecast_id, session)
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast not found")

    if forecast.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if forecast.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Forecast is not completed yet")

    forecast_items = get_forecast_items(forecast_id, session)
    if not forecast_items:
        raise HTTPException(status_code=404, detail="No forecast items found")

    logger.info(f"DEBUG: Total forecast_items: {len(forecast_items)}")

    items_data = defaultdict(lambda: {
        'total_predicted': 0.0,
        'probabilities': [],
        'days_with_sales': 0,
        'total_days': 0,
    })

    for item in forecast_items:
        data = items_data[item.item_id]
        data['total_predicted'] += item.predicted_sales
        data['probabilities'].append(item.probability_of_sale)
        data['total_days'] += 1
        if item.predicted_sales > 0:
            data['days_with_sales'] += 1

    logger.info(f"DEBUG: Unique items in items_data: {len(items_data)}")

    summary_items = []
    total_order = 0

    for current_item_id, data in items_data.items():
        avg_prob = np.mean(data['probabilities']) if data['probabilities'] else 0
        avg_daily_sales = data['total_predicted'] / data['total_days']

        recommended = int(np.ceil(data['total_predicted']))
        total_order += recommended

        if avg_daily_sales > 3:
            risk_level = "low"
            risk_description = "Товар быстро продаётся"
        elif avg_daily_sales > 1:
            risk_level = "medium"
            risk_description = "Средняя скорость продаж"
        else:
            risk_level = "high"
            risk_description = "Риск порчи (медленные продажи)"

        summary_items.append(SummaryItemResponse(
            item_id=current_item_id,
            total_predicted_sales=round(data['total_predicted'], 2),
            avg_daily_probability=round(avg_prob, 3),
            avg_daily_sales=round(avg_daily_sales, 2),
            days_with_expected_sales=data['days_with_sales'],
            total_days=data['total_days'],
            recommended_order=recommended,
            risk_level=risk_level,
            risk_description=risk_description
        ))

    logger.info(f"DEBUG: summary_items count: {len(summary_items)}")

    # сортируем по recommended_order (убывание) — самые важные товары сверху
    summary_items.sort(key=lambda x: x.recommended_order, reverse=True)

    if item_id:
        summary_items = [item for item in summary_items if item.item_id == item_id]
        if not summary_items:
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
        logger.info(f"DEBUG: After filtering by item_id={item_id}, count: {len(summary_items)}")

    dates = [item.forecast_date for item in forecast_items]
    period_start = min(dates).isoformat()
    period_end = max(dates).isoformat()

    return SummaryResponse(
        forecast_id=forecast_id,
        store_id=forecast.store_id,
        period_start=period_start,
        period_end=period_end,
        horizon_days=forecast.horizon_days,
        alpha=forecast.alpha,
        total_items=len(items_data),
        total_order_recommendation=total_order,
        items=summary_items
    )


class ScenarioData(BaseModel):
    alpha: float
    total_predicted: float
    recommended_order: int
    risk: str


class ScenarioItemResponse(BaseModel):
    item_id: str
    baseline: ScenarioData
    balanced: ScenarioData
    optimal: ScenarioData
    your_variant: ScenarioData


class ScenariosResponse(BaseModel):
    forecast_id: int
    store_id: str
    period: str
    total_items: int
    items: List[ScenarioItemResponse]


@forecast_router.get("/{forecast_id}/scenarios", response_model=ScenariosResponse)
def get_forecast_scenarios(
        forecast_id: int,
        item_id: Optional[str] = None,
        current_user: User = Depends(get_current_user_universal),
        session: Session = Depends(get_session)
):
    """
    Сравнение сценариев для разных alpha.
    Запускает модель 3 раза с разными alpha.
    """
    forecast = get_forecast_by_id(forecast_id, session)
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast not found")

    if forecast.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    scenarios = {
        'baseline': 0.5,
        'balanced': 0.35,
        'optimal': 0.2,
    }

    try:
        dept_ids = json.loads(forecast.dept_ids)
        if isinstance(dept_ids, str):
            dept_ids = [dept_ids]
    except (json.JSONDecodeError, TypeError):
        dept_ids = [d.strip() for d in forecast.dept_ids.split(',')]

    logger.info(f"Parsed dept_ids: {dept_ids}")

    SALES_PATH = '/app/data/sales_train_evaluation.csv'
    CALENDAR_PATH = '/app/data/calendar.csv'
    PRICES_PATH = '/app/data/sell_prices.csv'

    if ',' in forecast.store_id:
        store_ids = forecast.store_id.split(',')
    else:
        store_ids = forecast.store_id

    scenario_results = {}
    for name, alpha in scenarios.items():
        logger.info(f"Running scenario {name} (alpha={alpha})...")
        items = run_forecast_model(
            sales_path=SALES_PATH,
            calendar_path=CALENDAR_PATH,
            prices_path=PRICES_PATH,
            store_id=store_ids,
            dept_ids=dept_ids,
            horizon_days=forecast.horizon_days,
            alpha=alpha
        )

        grouped = defaultdict(float)
        for item in items:
            grouped[item['item_id']] += item['predicted_sales']
        scenario_results[name] = grouped

    your_variant_items = get_forecast_items(forecast_id, session)
    your_variant = defaultdict(float)
    for item in your_variant_items:
        your_variant[item.item_id] += item.predicted_sales

    all_item_ids = set()
    for data in scenario_results.values():
        all_item_ids.update(data.keys())
    all_item_ids.update(your_variant.keys())

    def make_scenario_dict(total, alpha):
        order = int(np.ceil(total))

        if alpha >= 0.45:
            risk = "high (baseline, риск порчи)"
        elif alpha >= 0.30:
            risk = "medium (сбалансированный)"
        elif alpha >= 0.15:
            risk = "low (консервативный)"
        else:
            risk = "very low (агрессивно консервативный)"

        return ScenarioData(
            alpha=alpha,
            total_predicted=round(total, 2),
            recommended_order=order,
            risk=risk
        )

    scenario_items = []
    for current_item_id in sorted(all_item_ids):
        scenario_items.append(ScenarioItemResponse(
            item_id=current_item_id,
            baseline=make_scenario_dict(scenario_results['baseline'].get(current_item_id, 0), 0.5),
            balanced=make_scenario_dict(scenario_results['balanced'].get(current_item_id, 0), 0.35),
            optimal=make_scenario_dict(scenario_results['optimal'].get(current_item_id, 0), 0.2),
            your_variant=make_scenario_dict(your_variant.get(current_item_id, 0), forecast.alpha)
        ))

    if item_id:
        scenario_items = [item for item in scenario_items if item.item_id == item_id]
        if not scenario_items:
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
        logger.info(f"DEBUG: After filtering by item_id={item_id}, count: {len(scenario_items)}")

    dates = [item.forecast_date for item in your_variant_items]
    period = f"{min(dates).isoformat()} to {max(dates).isoformat()}" if dates else ""

    return ScenariosResponse(
        forecast_id=forecast_id,
        store_id=forecast.store_id,
        period=period,
        total_items=len(scenario_items),
        items=scenario_items
    )


@forecast_router.get("/{forecast_id}/download")
def download_forecast(
        forecast_id: int,
        format: str = "detailed",
        current_user: User = Depends(get_current_user_universal),
        session: Session = Depends(get_session)
):
    """
    Скачать результат прогноза как CSV.

    format:
    - detailed: детальный прогноз по дням (по умолчанию)
    - summary: агрегированный план закупок (для менеджера)
    """
    forecast = get_forecast_by_id(forecast_id, session)
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast not found")

    if forecast.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if forecast.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Forecast is not completed yet")

    forecast_items = get_forecast_items(forecast_id, session)

    output = io.StringIO()
    writer = csv.writer(output)

    if format == "summary":
        writer.writerow(["item_id", "total_predicted_sales", "recommended_order", "risk_level"])

        items_data = defaultdict(lambda: {'total': 0.0, 'probabilities': [], 'days': 0})
        for item in forecast_items:
            data = items_data[item.item_id]
            data['total'] += item.predicted_sales
            data['probabilities'].append(item.probability_of_sale)
            data['days'] += 1

        for current_item_id, data in sorted(items_data.items(), key=lambda x: x[1]['total'], reverse=True):
            avg_prob = np.mean(data['probabilities'])
            avg_daily_sales = data['total'] / data['days']
            recommended = int(np.ceil(data['total']))

            if avg_daily_sales > 3:
                risk = "low"
            elif avg_daily_sales > 1:
                risk = "medium"
            else:
                risk = "high"

            writer.writerow([current_item_id, round(data['total'], 2), recommended, risk])

        filename = f"forecast_{forecast_id}_summary.csv"

    else:
        writer.writerow(["item_id", "date", "predicted_sales", "probability_of_sale", "volume"])

        for item in forecast_items:
            writer.writerow([
                item.item_id,
                item.forecast_date.isoformat(),
                item.predicted_sales,
                item.probability_of_sale,
                item.volume
            ])

        filename = f"forecast_{forecast_id}_detailed.csv"

    output.seek(0)

    logger.info(f"Forecast {forecast_id} downloaded (format={format}) by user {current_user.email}")

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
