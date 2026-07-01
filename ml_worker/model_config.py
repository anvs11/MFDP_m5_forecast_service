import numpy as np

SEED = 42
np.random.seed(SEED)

ALPHAS = [round(0.5 - i * 0.01, 2) for i in range(50)]

DATA_PATHS = {
    'sales': 'data/sales_train_evaluation.csv',
    'calendar': 'data/calendar.csv',
    'prices': 'data/sell_prices.csv',
}

MODEL_OUTPUT_PATH = 'model/artifacts/hurdle_model.pkl'

DEFAULT_STATE_ID = 'CA'
DEFAULT_DEPT_IDS = ['FOODS_1', 'FOODS_2']

# гиперпараметры классификатора
CLF_PARAMS = {
    'n_estimators': 369,
    'learning_rate': 0.06779,
    'num_leaves': 52,
    'min_data_in_leaf': 86,
    'random_state': SEED,
    'verbose': -1,
}

# гиперпараметры регрессора
REG_PARAMS = {
    'n_estimators': 159,
    'learning_rate': 0.17661,
    'num_leaves': 54,
    'min_data_in_leaf': 200,
    'random_state': SEED,
    'verbose': -1,
}

# признаки и параметры
FEATURES = [
    'lag_7', 'lag_14', 'lag_21', 'lag_28',
    'rolling_mean_7', 'rolling_std_7',
    'sell_price', 'price_missing', 'is_active',
    'snap_high', 'snap_medium', 'snap_low',
    'is_top_event',
    'store_id',
    'wday', 'demand_level', 'price_bin'
]

CATEGORICAL_FEATURES = ['store_id', 'wday', 'demand_level', 'price_bin']

PIPELINE_PARAMS = {
    'active_window': 30,
    'active_threshold': 0,
}

# бизнес-параметры
# Асимметрия потерь: порча в 3 раза дороже дефицита
COST_OVER = 3.0   # штраф за overstock (порча)
COST_UNDER = 1.0  # штраф за understock (дефицит)

# Optuna
OPTUNA_PARAMS = {
    'n_trials': 30,
    'timeout': 900,
    'direction': 'minimize',
}

# разделение данных
# Test start — последние 28 дней (d_1914 = 2016-04-25)
TEST_START = 1914