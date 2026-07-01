import os
import pickle
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
from sklearn.base import BaseEstimator, TransformerMixin
import warnings

warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class DataPreparator:
    def __init__(self, store_id=None, state_id=None, dept_ids: List[str] = None):
        """
        Инициализация подготовщика данных
        """
        self.store_id = store_id
        self.state_id = state_id
        self.dept_ids = dept_ids or ['FOODS_1', 'FOODS_2']

    def load_and_prepare(self, sales_path, calendar_path, prices_path):
        sales = pd.read_csv(sales_path)
        calendar = pd.read_csv(calendar_path)
        prices = pd.read_csv(prices_path)

        subset_sales = sales[sales['dept_id'].isin(self.dept_ids)].copy()

        if self.store_id:
            subset_sales = subset_sales[subset_sales['store_id'] == self.store_id]
        elif self.state_id:
            subset_sales = subset_sales[subset_sales['state_id'] == self.state_id]

        days_cols = [col for col in sales.columns if col.startswith('d_')]

        subset_long = subset_sales.melt(
            id_vars=['item_id', 'dept_id', 'cat_id', 'store_id', 'state_id'],
            value_vars=days_cols,
            var_name='d',
            value_name='sales'
        )

        subset_long['sales'] = pd.to_numeric(subset_long['sales'], downcast='integer')

        calendar_subset = calendar[
            calendar['d'].isin(subset_long['d'].unique())
        ][[
            'd', 'wday', 'month', 'year',
            'event_name_1', 'event_type_1',
            'snap_CA', 'snap_TX', 'snap_WI',
            'wm_yr_wk'
        ]].copy()

        prices_subset = prices[
            (prices['item_id'].isin(subset_sales['item_id']))
        ][['store_id', 'item_id', 'wm_yr_wk', 'sell_price']].copy()

        prices_subset['sell_price'] = pd.to_numeric(prices_subset['sell_price'], downcast='float')

        df = subset_long.merge(calendar_subset, on='d', how='left')
        del subset_long, calendar_subset

        df = df.merge(prices_subset, on=['store_id', 'item_id', 'wm_yr_wk'], how='left')
        del prices_subset

        df["price_missing"] = df["sell_price"].isna().astype(int)

        df["sell_price"] = df.groupby(["store_id", "item_id"])["sell_price"].ffill()

        median_by_store_dept = df.groupby(["store_id", "dept_id"])["sell_price"].transform("median")
        df["sell_price"] = df["sell_price"].fillna(median_by_store_dept)

        df["sell_price"] = df["sell_price"].fillna(0)

        df['d_num'] = df['d'].str.replace('d_', '').astype(int)
        df = df.sort_values(['item_id', 'd_num']).reset_index(drop=True)

        del sales, calendar, prices, subset_sales

        logger.info(f"DataPreparator: Dataset prepared. Shape: {df.shape}")
        return df


class FeaturePipeline(BaseEstimator, TransformerMixin):
    def __init__(self, active_window=30, active_threshold=0, price_quantiles=None, top_events=None):
        self.active_window = active_window
        self.active_threshold = active_threshold
        self.price_quantiles = price_quantiles
        self.top_events = top_events
        self.fitted = False

    def fit(self, df, y=None):
        if self.price_quantiles is None:
            prices = df['sell_price'].dropna()
            self.price_quantiles = [
                prices.quantile(0.2),
                prices.quantile(0.4),
                prices.quantile(0.6),
                prices.quantile(0.8),
            ]

        if self.top_events is None:
            event_effect = df[df['event_name_1'].notna()].groupby('event_name_1')['sales'].mean()
            self.top_events = event_effect.nlargest(5).index.tolist()

        self.fitted = True
        return self

    def transform(self, df):
        df = df.copy()

        # 1. Лаги
        for lag in [7, 14, 21, 28]:
            df[f'lag_{lag}'] = df.groupby('item_id')['sales'].shift(lag)

        # 2. Скользящие окна
        df['rolling_mean_7'] = (
            df.groupby('item_id')['sales']
            .transform(lambda x: x.shift(1).rolling(7, min_periods=1).mean())
        )
        df['rolling_std_7'] = (
            df.groupby('item_id')['sales']
            .transform(lambda x: x.shift(1).rolling(7, min_periods=1).std())
        )
        df['rolling_std_7'] = df['rolling_std_7'].fillna(0)

        # 3. Календарные признаки
        def get_demand_level(wday):
            if wday in [1, 2]:
                return 'high'
            elif wday in [3, 7]:
                return 'medium'
            else:
                return 'low'

        df['demand_level'] = df['wday'].apply(get_demand_level).astype('category')

        # 4. Ценовые признаки
        bins = [-np.inf] + self.price_quantiles + [np.inf]
        labels = ['q0_ultra_low', 'q1_low', 'q2_mid', 'q3_high', 'q4_ultra_high']
        df['price_bin'] = pd.cut(
            df['sell_price'],
            bins=bins,
            labels=labels,
            include_lowest=True
        ).astype('category')

        # 5. Флаги активности
        df['is_active'] = (
            df.groupby('item_id')['sales']
            .transform(lambda x: x.shift(1).rolling(self.active_window, min_periods=1).sum() > self.active_threshold)
        ).astype(int)

        # 6. Взаимодействия: snap_{state} × demand_level
        # Динамически определяем штат
        df['snap'] = df.apply(
            lambda row: row[f'snap_{row["state_id"]}'] if f'snap_{row["state_id"]}' in df.columns else 0,
            axis=1
        )

        df['snap_high'] = (df['snap'] * (df['demand_level'] == 'high')).astype(int)
        df['snap_medium'] = (df['snap'] * (df['demand_level'] == 'medium')).astype(int)
        df['snap_low'] = (df['snap'] * (df['demand_level'] == 'low')).astype(int)

        # 7. События
        df['is_top_event'] = df['event_type_1'].isin(['Sporting', 'Religious', 'Cultural']).astype(int)
        for event in self.top_events:
            col_name = f'is_{event.lower().replace(" ", "_")}'
            df[col_name] = (df['event_name_1'] == event).astype(int)

        df['wday'] = df['wday'].astype('category')

        return df

    def fit_transform(self, df, y=None):
        self.fit(df, y)
        return self.transform(df)

class M5Forecaster:
    DEFAULT_FEATURES = [
        'lag_7', 'lag_14', 'lag_21', 'lag_28',
        'rolling_mean_7', 'rolling_std_7',
        'sell_price', 'price_missing', 'is_active',
        'snap_high', 'snap_medium', 'snap_low',
        'is_top_event',
        'store_id',
        'wday', 'demand_level', 'price_bin'
    ]

    DEFAULT_CATEGORICAL_FEATURES = ['store_id', 'wday', 'demand_level', 'price_bin']

    def __init__(self, model_path: str = None):
        base_dir = os.path.dirname(os.path.abspath(__file__))

        if model_path is None:
            model_path = os.path.join(base_dir, 'model', 'artifacts', 'hurdle_model.pkl')
        elif not os.path.isabs(model_path):
            model_path = os.path.join(base_dir, model_path)

        logger.info(f"Loading model from {model_path}")
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)

        self.clf = model_data['clf']
        self.regs = model_data['regs']
        self.pipeline = model_data['pipeline']

        self.features = model_data.get('features', self.DEFAULT_FEATURES)
        self.categorical_features = model_data.get('categorical_features', self.DEFAULT_CATEGORICAL_FEATURES)

        logger.info(f"Model loaded. Available alphas: {list(self.regs.keys())}")
        logger.info(f"Features count: {len(self.features)}")

    def predict(
            self,
            sales_path: str,
            calendar_path: str,
            prices_path: str,
            store_id: str,
            dept_ids: List[str],
            horizon_days: int,
            alpha: float
    ) -> List[Dict]:
        logger.info(f"Starting forecast: store={store_id}, depts={dept_ids}, horizon={horizon_days}, alpha={alpha}")

        if alpha not in self.regs:
            available = list(self.regs.keys())
            raise ValueError(f"Alpha {alpha} not available. Available: {available}")

        state_id = store_id.split('_')[0]
        logger.info(f"Extracted state_id: {state_id}")

        # 1. Загружаем данные для конкретного магазина
        preparator = DataPreparator(store_id=store_id, dept_ids=dept_ids)
        df = preparator.load_and_prepare(sales_path, calendar_path, prices_path)

        # 2. Применяем FeaturePipeline
        df_feat = self.pipeline.transform(df)

        # 3. Берём последние horizon_days
        max_d = df_feat['d_num'].max()
        forecast_d_nums = list(range(max_d - horizon_days + 1, max_d + 1))
        df_forecast = df_feat[df_feat['d_num'].isin(forecast_d_nums)].copy()

        # 4. Предсказания
        X = df_forecast[self.features].copy()

        for col in self.categorical_features:
            if col in X.columns:
                X[col] = X[col].astype('category')

        P_positive = self.clf.predict_proba(X)[:, 1]
        reg = self.regs[alpha]
        volume = reg.predict(X)

        preds = P_positive * volume
        preds = np.maximum(0, preds)
        preds = np.round(preds)

        calendar_df = pd.read_csv(calendar_path)
        d_to_date = dict(zip(
            calendar_df['d'].str.replace('d_', '').astype(int),
            pd.to_datetime(calendar_df['date'])
        ))

        forecast_items = []
        for i, (idx, row) in enumerate(df_forecast.iterrows()):
            d_num = int(row['d_num'])
            forecast_date = d_to_date.get(d_num, datetime.now().date())
            if hasattr(forecast_date, 'date'):
                forecast_date = forecast_date.date()

            forecast_items.append({
                'item_id': row['item_id'],
                'date': forecast_date,
                'predicted_sales': float(preds[i]),
                'probability_of_sale': float(P_positive[i]),
                'volume': float(volume[i])
            })

        logger.info(f"Generated {len(forecast_items)} forecast items")
        return forecast_items

    def _d_num_to_date(self, d_num: int, calendar_path: str) -> datetime:
        calendar = pd.read_csv(calendar_path)
        row = calendar[calendar['d'] == f'd_{d_num}']
        if not row.empty:
            return pd.to_datetime(row.iloc[0]['date']).date()
        return datetime.now().date()


def run_forecast(
        sales_path: str,
        calendar_path: str,
        prices_path: str,
        store_id: str,
        dept_ids: List[str],
        horizon_days: int,
        alpha: float,
        model_path: str = None
) -> List[Dict]:
    """
    Точка входа для воркера.
    store_id: ID одного магазина (например, 'CA_1')
    """
    logger.info(f"Starting forecast: store={store_id}, depts={dept_ids}, horizon={horizon_days}, alpha={alpha}")

    preparator = DataPreparator(
        store_id=store_id,
        dept_ids=dept_ids
    )
    df = preparator.load_and_prepare(sales_path, calendar_path, prices_path)

    logger.info(f"DataPreparator: Dataset prepared. Shape: {df.shape}")

    if df.empty:
        logger.error(
            f"Dataset is empty! Store: {store_id}, Depts: {dept_ids}")
        return []

    forecaster = M5Forecaster(model_path=model_path)

    df = forecaster.pipeline.transform(df)
    logger.info(f"FeaturePipeline applied. Shape: {df.shape}")

    max_d = int(df['d_num'].max())
    forecast_d_nums = list(range(max_d - horizon_days + 1, max_d + 1))
    df_forecast = df[df['d_num'].isin(forecast_d_nums)].copy()

    X = df_forecast[forecaster.features].copy()

    for col in forecaster.categorical_features:
        if col in X.columns:
            X[col] = X[col].astype('category')

    logger.info(f"Predicting with {len(X)} rows")

    P_positive = forecaster.clf.predict_proba(X)[:, 1]
    reg = forecaster.regs[alpha]
    volume = reg.predict(X)

    preds = P_positive * volume
    preds = np.maximum(0, preds)
    preds = np.round(preds)

    calendar_df = pd.read_csv(calendar_path)
    d_to_date = dict(zip(
        calendar_df['d'].str.replace('d_', '').astype(int),
        pd.to_datetime(calendar_df['date'])
    ))

    forecast_items = []
    for i, (idx, row) in enumerate(df_forecast.iterrows()):
        d_num = int(row['d_num'])
        forecast_date = d_to_date.get(d_num, datetime.now().date())
        if hasattr(forecast_date, 'date'):
            forecast_date = forecast_date.date()

        forecast_items.append({
            'item_id': row['item_id'],
            'date': forecast_date,
            'predicted_sales': float(preds[i]),
            'probability_of_sale': float(P_positive[i]),
            'volume': float(volume[i])
        })

    logger.info(f"Generated {len(forecast_items)} forecast items")
    return forecast_items
