import pandas as pd
import numpy as np
import pickle
import os
import time
from lightgbm import LGBMRegressor, LGBMClassifier
from forecaster import DataPreparator, FeaturePipeline
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEED = 42
np.random.seed(SEED)

FEATURES = [
    'lag_7', 'lag_14', 'lag_21', 'lag_28',
    'rolling_mean_7', 'rolling_std_7',
    'sell_price', 'is_active',
    'snap_high', 'snap_medium', 'snap_low',
    'is_top_event',
    'store_id',
    'wday', 'demand_level', 'price_bin'
]

CATEGORICAL_FEATURES = ['store_id', 'wday', 'demand_level', 'price_bin']


def train_model(
        sales_path: str,
        calendar_path: str,
        prices_path: str,
        state_id: str = 'CA',
        dept_ids: list = None,
        test_start: int = 1914,
        alphas: list = None,
        output_path: str = 'model/artifacts/hurdle_model.pkl'
):
    """
    Обучает Hurdle Model на всех магазинах указанного штата.
    """
    dept_ids = dept_ids or ['FOODS_1', 'FOODS_2']
    alphas = alphas or [0.5, 0.4, 0.3, 0.2, 0.1]

    logger.info(f"Starting training: state={state_id}, depts={dept_ids}, alphas={len(alphas)} models")

    preparator = DataPreparator(state_id=state_id, cat_ids=dept_ids)
    df = preparator.load_and_prepare(sales_path, calendar_path, prices_path)

    df_train = df[df['d_num'] < test_start].copy()
    logger.info(f"Train dataset: {df_train.shape}")

    pipeline = FeaturePipeline()
    df_train_feat = pipeline.fit_transform(df_train)

    df_train_clean = df_train_feat.dropna(subset=['lag_28', 'sales'])
    logger.info(f"Clean dataset: {df_train_clean.shape}")

    X_train = df_train_clean[FEATURES]
    y_train = df_train_clean['sales']
    y_train_binary = (y_train > 0).astype(int)

    logger.info("Training classifier...")
    start = time.time()

    clf_params = {
        'n_estimators': 300,
        'learning_rate': 0.05,
        'num_leaves': 50,
        'min_data_in_leaf': 100,
        'random_state': SEED,
        'verbose': -1
    }

    clf = LGBMClassifier(**clf_params)
    clf.fit(X_train, y_train_binary, categorical_feature=CATEGORICAL_FEATURES)
    logger.info(f"Classifier trained in {time.time() - start:.2f}s")

    regs = {}
    reg_params = {
        'n_estimators': 300,
        'learning_rate': 0.05,
        'num_leaves': 50,
        'min_data_in_leaf': 100,
        'random_state': SEED,
        'verbose': -1
    }

    X_train_pos = X_train[y_train > 0]
    y_train_pos = y_train[y_train > 0]
    logger.info(f"Positive samples for regression: {len(y_train_pos)}")

    for i, alpha in enumerate(alphas):
        logger.info(f"Training regressor {i+1}/{len(alphas)} with alpha={alpha}...")
        start = time.time()

        reg = LGBMRegressor(objective='quantile', alpha=alpha, **reg_params)
        reg.fit(X_train_pos, y_train_pos, categorical_feature=CATEGORICAL_FEATURES)

        regs[alpha] = reg
        logger.info(f"Regressor alpha={alpha} trained in {time.time() - start:.2f}s")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    model_data = {
        'clf': clf,
        'regs': regs,
        'pipeline': pipeline,
        'features': FEATURES,
        'categorical_features': CATEGORICAL_FEATURES,
        'alphas': alphas,
        'state_id': state_id
    }

    with open(output_path, 'wb') as f:
        pickle.dump(model_data, f)

    logger.info(f"Model saved to {output_path}")
    logger.info(f"Available alphas: {alphas}")


if __name__ == '__main__':
    SALES_PATH = 'data/sales_train_evaluation.csv'
    CALENDAR_PATH = 'data/calendar.csv'
    PRICES_PATH = 'data/sell_prices.csv'

    # Alpha от 0.5 до 0.01 с шагом 0.01 (50 моделей)
    ALPHAS = [round(0.5 - i * 0.01, 2) for i in range(50)]

    train_model(
        sales_path=SALES_PATH,
        calendar_path=CALENDAR_PATH,
        prices_path=PRICES_PATH,
        state_id='CA',
        dept_ids=['FOODS_1', 'FOODS_2'],
        alphas=ALPHAS,
        output_path='model/artifacts/hurdle_model.pkl'
    )
