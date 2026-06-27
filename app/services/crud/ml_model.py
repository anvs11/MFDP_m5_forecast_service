from sqlmodel import Session, select
from typing import Optional
from models.ml_model import MLModel
import logging

logger = logging.getLogger(__name__)


def get_model_by_id(model_id: str, session: Session) -> Optional[MLModel]:
    """Получить ML модель по model_id"""
    statement = select(MLModel).where(MLModel.model_id == model_id)
    return session.exec(statement).first()


def get_all_models(session: Session) -> list[MLModel]:
    """Получить все активные ML модели"""
    statement = select(MLModel).where(MLModel.is_active == True)
    return session.exec(statement).all()


def create_model(model: MLModel, session: Session) -> MLModel:
    """Создать новую ML модель"""
    session.add(model)
    session.commit()
    session.refresh(model)
    logger.info(f"ML model created: {model.model_id}")
    return model