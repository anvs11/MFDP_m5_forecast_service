import pandas as pd
import numpy as np
import pickle
import os
import time
import copy
import argparse
from lightgbm import LGBMRegressor, LGBMClassifier
from sklearn.base import BaseEstimator, TransformerMixin
import logging

from model_config import (
    SEED, ALPHAS, DATA_PATHS, MODEL_OUTPUT_PATH,
    DEFAULT_STATE_ID, DEFAULT_DEPT_IDS,
    CLF_PARAMS, REG_PARAMS,
    FEATURES, CATEGORICAL_FEATURES, PIPELINE_PARAMS,
    COST_OVER, COST_UNDER,
    OPTUNA_PARAMS, TEST_START
)

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
from forecaster import DataPreparator, FeaturePipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def simulated_cost_loss(y_true, y_pred, cost_over=COST_OVER, cost_under=COST_UNDER):
    """Бизнес-метрика: симулирует потери от ошибок прогноза."""
    over = np.maximum(y_pred - y_true, 0)
    under = np.maximum(y_true - y_pred, 0)
    return np.mean(cost_over * over + cost_under * under)


def create_walk_forward_splits(df, test_start, n_folds=3, val_window=200, min_train_days=None):
    """Создает фолды для Walk-Forward валидации"""
    end_point = test_start - 1

    if min_train_days is None:
        min_train_days = val_window * 2

    required_history = end_point - (n_folds * val_window)

    if required_history < min_train_days:
        raise ValueError(
            f"История слишком короткая! Для {n_folds} фолдов с окном {val_window} "
            f"требуется минимум {min_train_days} дней на обучение."
        )

    splits = []
    for i in range(n_folds):
        val_end = end_point - (n_folds - 1 - i) * val_window
        val_start = val_end - val_window + 1
        train_end = val_start - 1

        splits.append({
            'train_end': train_end,
            'val_start': val_start,
            'val_end': val_end,
            'description': f"Fold {i + 1}: Train [d_1–d_{train_end}], Val [d_{val_start}–d_{val_end}]"
        })
        logger.info(f"Fold {i + 1}: Train [d_1–d_{train_end}], Val [d_{val_start}–d_{val_end}]")

    return splits


def objective(trial, df_clean, pipeline_template, splits, features, categorical_features):
    """
    Функция для Optuna с Walk-Forward валидацией.
    Оптимизирует SCL (асимметричная бизнес-метрика).
    """
    clf_params = {
        'n_estimators': trial.suggest_int('clf_n_estimators', 100, 500),
        'learning_rate': trial.suggest_float('clf_learning_rate', 0.01, 0.2, log=True),
        'num_leaves': trial.suggest_int('clf_num_leaves', 20, 100),
        'min_data_in_leaf': trial.suggest_int('clf_min_data_in_leaf', 50, 500),
        'random_state': SEED,
        'verbose': -1
    }

    reg_params = {
        'n_estimators': trial.suggest_int('reg_n_estimators', 100, 500),
        'learning_rate': trial.suggest_float('reg_learning_rate', 0.01, 0.2, log=True),
        'num_leaves': trial.suggest_int('reg_num_leaves', 20, 100),
        'min_data_in_leaf': trial.suggest_int('reg_min_data_in_leaf', 50, 500),
        'random_state': SEED,
        'verbose': -1
    }

    fold_scores = []
    for split in splits:
        df_train_fold = df_clean[df_clean['d_num'] <= split['train_end']].copy()
        df_val_fold = df_clean[(df_clean['d_num'] >= split['val_start']) &
                               (df_clean['d_num'] <= split['val_end'])].copy()

        df_combined = pd.concat([df_train_fold, df_val_fold], ignore_index=True)
        df_combined = df_combined.sort_values(['item_id', 'd_num']).reset_index(drop=True)

        pipeline = copy.deepcopy(pipeline_template)

        pipeline.fit(df_train_fold)

        df_combined_feat = pipeline.transform(df_combined)

        df_train_feat = df_combined_feat[df_combined_feat['d_num'] <= split['train_end']].copy()
        df_val_feat = df_combined_feat[df_combined_feat['d_num'] >= split['val_start']].copy()

        df_train_clean = df_train_feat.dropna(subset=['lag_28', 'sales']).copy()
        df_val_clean = df_val_feat.dropna(subset=['lag_28', 'sales']).copy()

        if len(df_val_clean) == 0:
            continue

        X_train = df_train_clean[features]
        y_train = df_train_clean['sales']
        X_val = df_val_clean[features]
        y_val = df_val_clean['sales']

        for col in categorical_features:
            X_train[col] = X_train[col].astype('category')
            X_val[col] = X_val[col].astype('category')

        y_train_binary = (y_train > 0).astype(int)
        clf = LGBMClassifier(**clf_params)
        clf.fit(X_train, y_train_binary, categorical_feature=categorical_features)

        # Обучение регрессора (alpha=0.5 для стабильности)
        reg = LGBMRegressor(objective='quantile', alpha=0.5, **reg_params)
        reg.fit(X_train[y_train > 0], y_train[y_train > 0], categorical_feature=categorical_features)

        P_positive = clf.predict_proba(X_val)[:, 1]
        volume = reg.predict(X_val)
        preds = P_positive * volume
        preds = np.maximum(0, np.round(preds))

        # SCL — основная метрика для оптимизации
        fold_scl = simulated_cost_loss(y_val, preds)
        fold_mae = np.mean(np.abs(y_val - preds))

        fold_scores.append(fold_scl)
        logger.info(f"  {split['description']}: SCL = {fold_scl:.3f}, MAE = {fold_mae:.3f}")

    mean_scl = np.mean(fold_scores)
    logger.info(f"  Средний SCL: {mean_scl:.3f}\n")

    return mean_scl


def train_model(
        sales_path: str = None,
        calendar_path: str = None,
        prices_path: str = None,
        state_id: str = DEFAULT_STATE_ID,
        dept_ids: list = None,
        test_start: int = TEST_START,
        alphas: list = None,
        output_path: str = MODEL_OUTPUT_PATH,
        run_optuna: bool = False
):
    """
    Обучает Hurdle Model на всех магазинах указанного штата.

    Args:
        run_optuna: Если True, запускает Optuna для подбора гиперпараметров.
                   Если False, использует параметры из model_config.py
    """

    sales_path = sales_path or DATA_PATHS['sales']
    calendar_path = calendar_path or DATA_PATHS['calendar']
    prices_path = prices_path or DATA_PATHS['prices']

    dept_ids = dept_ids or DEFAULT_DEPT_IDS
    alphas = alphas or ALPHAS

    logger.info(f"Starting training: state={state_id}, depts={dept_ids}, alphas={len(alphas)} models")

    preparator = DataPreparator(state_id=state_id, dept_ids=dept_ids)
    df = preparator.load_and_prepare(sales_path, calendar_path, prices_path)

    df_train = df[df['d_num'] < test_start].copy()
    logger.info(f"Train dataset: {df_train.shape}")

    pipeline = FeaturePipeline(**PIPELINE_PARAMS)
    df_train_feat = pipeline.fit_transform(df_train)

    df_train_clean = df_train_feat.dropna(subset=['lag_28', 'sales'])
    logger.info(f"Clean dataset: {df_train_clean.shape}")

    X_train = df_train_clean[FEATURES]
    y_train = df_train_clean['sales']
    y_train_binary = (y_train > 0).astype(int)

    for col in CATEGORICAL_FEATURES:
        X_train[col] = X_train[col].astype('category')

    # Optuna (опционально)
    clf_params_to_use = CLF_PARAMS.copy()
    reg_params_to_use = REG_PARAMS.copy()

    if run_optuna:
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)

        logger.info("Запуск Optuna для подбора гиперпараметров...")
        wf_splits = create_walk_forward_splits(df, test_start=test_start, n_folds=3, val_window=200)

        start_time = time.time()
        study = optuna.create_study(direction=OPTUNA_PARAMS['direction'])
        study.optimize(
            lambda trial: objective(trial, df, pipeline, wf_splits, FEATURES, CATEGORICAL_FEATURES),
            n_trials=OPTUNA_PARAMS['n_trials'],
            timeout=OPTUNA_PARAMS['timeout']
        )
        time_optuna = time.time() - start_time

        best_params = study.best_params
        logger.info(f"\nЛучшие гиперпараметры:")
        for k, v in best_params.items():
            logger.info(f"   {k}: {v}")
        logger.info(f"Лучший средний SCL: {study.best_value:.3f}")
        logger.info(f"Время подбора: {time_optuna:.1f} сек")

        clf_params_to_use = {k.replace('clf_', ''): v for k, v in best_params.items() if k.startswith('clf_')}
        reg_params_to_use = {k.replace('reg_', ''): v for k, v in best_params.items() if k.startswith('reg_')}
        clf_params_to_use.update({'random_state': SEED, 'verbose': -1})
        reg_params_to_use.update({'random_state': SEED, 'verbose': -1})

        logger.info(f"Обновлённые параметры clf: {clf_params_to_use}")
        logger.info(f"Обновлённые параметры reg: {reg_params_to_use}")

    logger.info("Training classifier...")
    start = time.time()

    clf = LGBMClassifier(**clf_params_to_use)
    clf.fit(X_train, y_train_binary, categorical_feature=CATEGORICAL_FEATURES)
    logger.info(f"Classifier trained in {time.time() - start:.2f}s")

    regs = {}
    X_train_pos = X_train[y_train > 0]
    y_train_pos = y_train[y_train > 0]
    logger.info(f"Positive samples for regression: {len(y_train_pos)}")

    for i, alpha in enumerate(alphas):
        logger.info(f"Training regressor {i + 1}/{len(alphas)} with alpha={alpha}...")
        start = time.time()

        reg = LGBMRegressor(objective='quantile', alpha=alpha, **reg_params_to_use)
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
        'state_id': state_id,
        'clf_params': clf_params_to_use,
        'reg_params': reg_params_to_use,
    }

    with open(output_path, 'wb') as f:
        pickle.dump(model_data, f)

    logger.info(f"Model saved to {output_path}")
    logger.info(f"Available alphas: {alphas}")

    if run_optuna:
        logger.info("Необходимо обновить model_config.py следующими значениями:")
        logger.info(f"CLF_PARAMS = {clf_params_to_use}")
        logger.info(f"REG_PARAMS = {reg_params_to_use}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train M5 Forecast Model')
    parser.add_argument('--optuna', action='store_true',
                        help='Запустить Optuna для подбора гиперпараметров')
    args = parser.parse_args()

    train_model(
        run_optuna=args.optuna,
    )
