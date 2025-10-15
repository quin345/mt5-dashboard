import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta

pd.set_option("display.max_columns", 500)
pd.set_option("display.width", 1500)
pd.set_option("display.float_format", lambda x: "%.5f" % x)


class VolatilityProcessor:
    def __init__(self, lookback_periods=(5, 10, 20)):
        self.lookback_periods = lookback_periods
        self.scaler = StandardScaler()

    def calculate_volatility_features(self, df):
        df = df.copy()

        # Basic calculations
        df["returns"] = df["close"].pct_change().fillna(0)
        df["log_returns"] = (np.log(df["close"]) - np.log(df["close"].shift(1))).fillna(
            0
        )

        # True Range
        df["true_range"] = np.maximum(
            df["high"] - df["low"],
            np.maximum(
                abs(df["high"] - df["close"].shift(1).fillna(df["high"])),
                abs(df["low"] - df["close"].shift(1).fillna(df["low"])),
            ),
        )

        # ATR and volatility
        for period in self.lookback_periods:
            df[f"atr_{period}"] = (
                df["true_range"].rolling(window=period, min_periods=1).mean()
            )
            df[f"volatility_{period}"] = (
                df["returns"].rolling(window=period, min_periods=1).std()
            )

        # Parkinson volatility
        df["parkinson_vol"] = np.sqrt(
            1 / (4 * np.log(2)) * np.power(np.log(df["high"].div(df["low"])), 2)
        )

        # Garman-Klass volatility
        df["garman_klass_vol"] = np.sqrt(
            0.5 * np.power(np.log(df["high"].div(df["low"])), 2)
            - (2 * np.log(2) - 1) * np.power(np.log(df["close"].div(df["open"])), 2)
        )

        # Relative volatility changes
        for period in self.lookback_periods:
            df[f"vol_change_{period}"] = df[f"volatility_{period}"].div(
                df[f"volatility_{period}"].shift(1)
            )

        # Replace all infinities and NaN
        for col in df.columns:
            if df[col].dtype == float:
                df[col] = df[col].replace([np.inf, -np.inf], np.nan).fillna(0)

        return df

    def prepare_features(self, df):
        feature_cols = []

        # Time-based features - correct time transformation
        time = pd.to_datetime(df["time"], unit="s")

        # Hours (0-23) -> radians (0-2π)
        hours = time.dt.hour.values
        df["hour_sin"] = np.sin(2 * np.pi * hours / 24.0)
        df["hour_cos"] = np.cos(2 * np.pi * hours / 24.0)

        # Week days (0-6) -> radians (0-2π)
        days = time.dt.dayofweek.values
        df["day_sin"] = np.sin(2 * np.pi * days / 7.0)
        df["day_cos"] = np.cos(2 * np.pi * days / 7.0)

        # Select features
        for period in self.lookback_periods:
            feature_cols.extend(
                [f"atr_{period}", f"volatility_{period}", f"vol_change_{period}"]
            )

        feature_cols.extend(
            [
                "parkinson_vol",
                "garman_klass_vol",
                "hour_sin",
                "hour_cos",
                "day_sin",
                "day_cos",
            ]
        )

        # Create features DataFrame
        features = df[feature_cols].copy()

        # Final cleanup and scaling
        features = features.replace([np.inf, -np.inf], 0).fillna(0)
        scaled_features = self.scaler.fit_transform(features)

        return pd.DataFrame(
            scaled_features, columns=features.columns, index=features.index
        )

    def create_target(self, df, forward_window=12):
        future_vol = (
            df["returns"]
            .rolling(window=forward_window, min_periods=1, center=False)
            .std()
            .shift(-forward_window)
            .fillna(0)
        )

        return future_vol

    def prepare_dataset(self, df, forward_window=12):
        print("\n=== Preparing Dataset ===")
        print("Initial shape:", df.shape)

        df = self.calculate_volatility_features(df)
        print("After calculating features:", df.shape)

        features = self.prepare_features(df)
        target = self.create_target(df, forward_window)

        print("Final shape:", features.shape)
        return features, target


def check_mt5_data(symbol="EURUSD"):
    if not mt5.initialize():
        print(f"MT5 initialization error: {mt5.last_error()}")
        return None

    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 10000)
    mt5.shutdown()

    if rates is None:
        return None

    return pd.DataFrame(rates)


def main():
    symbol = "EURUSD"
    rates_frame = check_mt5_data(symbol)

    if rates_frame is not None:
        print("\n=== Processing Hourly Data for Volatility Analysis ===")
        processor = VolatilityProcessor(lookback_periods=(5, 10, 20))
        features, target = processor.prepare_dataset(rates_frame)

        print("\nFeature statistics:")
        print(features.describe())
        print("\nFeature columns:", features.columns.tolist())
        print("\nTarget statistics:")
        print(target.describe())
    else:
        print("Failed to process data: MT5 data retrieval error")


if __name__ == "__main__":
    main()


import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
from xgboost import XGBClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)
import matplotlib

matplotlib.use("Agg")  # It is important to set before pyplot import
import matplotlib.pyplot as plt
import seaborn as sns


class VolatilityProcessor:
    def __init__(self, lookback_periods=(5, 10, 20), volatility_threshold=75):
        """
        Args:
            lookback_periods: periods for calculating features
            volatility_threshold: percentile to define high volatility
        """
        self.lookback_periods = lookback_periods
        self.volatility_threshold = volatility_threshold
        self.scaler = StandardScaler()

    def calculate_features(self, df):
        df = df.copy()

        # Basic calculations
        df["returns"] = df["close"].pct_change()
        df["abs_returns"] = abs(df["returns"])

        # True Range
        df["true_range"] = np.maximum(
            df["high"] - df["low"],
            np.maximum(
                abs(df["high"] - df["close"].shift(1)),
                abs(df["low"] - df["close"].shift(1)),
            ),
        )

        # Volatility features
        for period in self.lookback_periods:
            # ATR
            df[f"atr_{period}"] = df["true_range"].rolling(window=period).mean()

            # Volatility
            df[f"volatility_{period}"] = df["returns"].rolling(period).std()

            # Extremes
            df[f"high_low_range_{period}"] = (
                df["high"].rolling(period).max() - df["low"].rolling(period).min()
            ) / df["close"]

            # Volatility acceleration
            df[f"volatility_change_{period}"] = df[f"volatility_{period}"] / df[
                f"volatility_{period}"
            ].shift(1)

        # Add sentiment indicators
        df["body_ratio"] = abs(df["close"] - df["open"]) / (df["high"] - df["low"])
        df["upper_shadow"] = (df["high"] - df[["open", "close"]].max(axis=1)) / (
            df["high"] - df["low"]
        )
        df["lower_shadow"] = (df[["open", "close"]].min(axis=1) - df["low"]) / (
            df["high"] - df["low"]
        )

        # Clear data
        for col in df.columns:
            if df[col].dtype == float:
                df[col] = df[col].replace([np.inf, -np.inf], np.nan)
                df[col] = df[col].fillna(method="ffill").fillna(0)

        return df

    def prepare_features(self, df):
        # Select model features
        feature_cols = []

        # Add time features
        time = pd.to_datetime(df["time"], unit="s")
        df["hour_sin"] = np.sin(2 * np.pi * time.dt.hour / 24)
        df["hour_cos"] = np.cos(2 * np.pi * time.dt.hour / 24)
        df["day_sin"] = np.sin(2 * np.pi * time.dt.dayofweek / 7)
        df["day_cos"] = np.cos(2 * np.pi * time.dt.dayofweek / 7)

        # Collect all features
        for period in self.lookback_periods:
            feature_cols.extend(
                [
                    f"atr_{period}",
                    f"volatility_{period}",
                    f"high_low_range_{period}",
                    f"volatility_change_{period}",
                ]
            )

        feature_cols.extend(
            [
                "body_ratio",
                "upper_shadow",
                "lower_shadow",
                "hour_sin",
                "hour_cos",
                "day_sin",
                "day_cos",
            ]
        )

        # Create DataFrame with features
        features = df[feature_cols].copy()
        features = features.replace([np.inf, -np.inf], 0).fillna(0)

        # Scale features
        scaled_features = self.scaler.fit_transform(features)

        return pd.DataFrame(scaled_features, columns=feature_cols, index=features.index)

    def create_target(self, df, forward_window=12):
        """Create binary label: 1 for high volatility, 0 for low volatility"""
        # Calculate future volatility
        future_vol = (
            df["returns"]
            .rolling(window=forward_window, min_periods=1, center=False)
            .std()
            .shift(-forward_window)
        )

        # Define threshold for high volatility
        vol_threshold = np.nanpercentile(future_vol, self.volatility_threshold)

        # Create binary labels
        target = (future_vol > vol_threshold).astype(int)
        target = target.fillna(0)

        return target

    def prepare_dataset(self, df, forward_window=12):
        print("\n=== Preparing Dataset ===")
        print("Initial shape:", df.shape)

        df = self.calculate_features(df)
        print("After calculating features:", df.shape)

        features = self.prepare_features(df)
        target = self.create_target(df, forward_window)

        print("Final shape:", features.shape)
        print(f"Positive class ratio: {target.mean():.2%}")

        return features, target


class VolatilityClassifier:
    def __init__(
        self, lookback_periods=(5, 10, 20), forward_window=12, volatility_threshold=75
    ):
        self.processor = VolatilityProcessor(lookback_periods, volatility_threshold)
        self.forward_window = forward_window

        self.model = XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=1,
            gamma=0.1,
            reg_alpha=0.1,
            reg_lambda=1,
            scale_pos_weight=1,
            random_state=42,
            n_jobs=-1,
            eval_metric=["auc", "error"],
        )

        self.feature_importance = None

    def prepare_data(self, rates_frame):
        features, target = self.processor.prepare_dataset(rates_frame)
        return features, target

    def create_train_test_split(self, features, target, test_size=0.2):
        split_idx = int(len(features) * (1 - test_size))

        X_train = features.iloc[:split_idx]
        X_test = features.iloc[split_idx:]
        y_train = target.iloc[:split_idx]
        y_test = target.iloc[split_idx:]

        return X_train, X_test, y_train, y_test

    def train(self, X_train, y_train, X_test, y_test):
        print("\n=== Training Model ===")
        print("Training set shape:", X_train.shape)
        print("Test set shape:", X_test.shape)

        # Train model
        eval_set = [(X_train, y_train), (X_test, y_test)]
        self.model.fit(X_train, y_train, eval_set=eval_set, verbose=True)

        # Save importance of features
        importance = self.model.feature_importances_
        self.feature_importance = pd.DataFrame(
            {"feature": X_train.columns, "importance": importance}
        ).sort_values("importance", ascending=False)

        # Evaluate model
        predictions = self.predict(X_test)
        metrics = self.calculate_metrics(y_test, predictions)

        return metrics

    def calculate_metrics(self, y_true, y_pred):
        metrics = {
            "Accuracy": accuracy_score(y_true, y_pred),
            "Precision": precision_score(y_true, y_pred),
            "Recall": recall_score(y_true, y_pred),
            "F1 Score": f1_score(y_true, y_pred),
        }

        # Error matrix
        cm = confusion_matrix(y_true, y_pred)
        print("\nConfusion Matrix:")
        print(cm)

        return metrics

    def predict(self, features):
        return self.model.predict(features)

    def predict_proba(self, features):
        return self.model.predict_proba(features)

    def plot_feature_importance(self):
        plt.figure(figsize=(12, 6))
        plt.bar(
            self.feature_importance["feature"], self.feature_importance["importance"]
        )
        plt.xticks(rotation=45, ha="right")
        plt.title("Feature Importance")
        plt.tight_layout()
        plt.show()

    def plot_confusion_matrix(self, y_true, y_pred):
        cm = confusion_matrix(y_true, y_pred)
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues")
        plt.title("Confusion Matrix")
        plt.ylabel("True Label")
        plt.xlabel("Predicted Label")
        plt.tight_layout()
        plt.show()


def check_mt5_data(symbol="EURUSD"):
    if not mt5.initialize():
        print(f"MT5 initialization error: {mt5.last_error()}")
        return None

    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 10000)
    mt5.shutdown()

    if rates is None:
        return None

    return pd.DataFrame(rates)


def main():
    symbol = "EURUSD"
    rates_frame = check_mt5_data(symbol)

    if rates_frame is not None:
        # Create and train model
        model = VolatilityClassifier(
            lookback_periods=(5, 10, 20), forward_window=12, volatility_threshold=75
        )
        features, target = model.prepare_data(rates_frame)

        # Split data
        X_train, X_test, y_train, y_test = model.create_train_test_split(
            features, target, test_size=0.2
        )

        # Train and evaluate
        metrics = model.train(X_train, y_train, X_test, y_test)
        print("\n=== Model Performance ===")
        for metric, value in metrics.items():
            print(f"{metric}: {value:.4f}")

        # Make forecasts
        predictions = model.predict(X_test)

        # Visualize results
        model.plot_feature_importance()
        model.plot_confusion_matrix(y_test, predictions)
    else:
        print("Failed to process data: MT5 data retrieval error")


if __name__ == "__main__":
    main()


import tkinter as tk
from tkinter import ttk
import matplotlib

matplotlib.use("Agg")  # It is important to set before pyplot import
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
import MetaTrader5 as mt5


class VolatilityPredictor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Volatility Predictor")
        self.geometry("600x600")

        # Initialize model
        self.model = VolatilityClassifier(
            lookback_periods=(5, 10, 20), forward_window=12, volatility_threshold=75
        )

        # Download and train model at start
        self.initialize_model()

        # Create interface
        self.create_gui()

        # Launch the update
        self.update_data()

    def initialize_model(self):
        rates_frame = check_mt5_data("EURUSD")
        if rates_frame is not None:
            features, target = self.model.prepare_data(rates_frame)
            X_train, X_test, y_train, y_test = self.model.create_train_test_split(
                features, target, test_size=0.2
            )
            self.model.train(X_train, y_train, X_test, y_test)

    def create_gui(self):
        # Upper panel with settings
        control_frame = ttk.Frame(self)
        control_frame.pack(fill="x", padx=2, pady=2)

        ttk.Label(control_frame, text="Symbol:").pack(side="left", padx=2)
        self.symbol_var = tk.StringVar(value="EURUSD")
        symbol_list = ["EURUSD", "GBPUSD", "USDJPY"]  # Simplified list
        ttk.Combobox(
            control_frame, textvariable=self.symbol_var, values=symbol_list, width=8
        ).pack(side="left", padx=2)

        ttk.Label(control_frame, text="Alert:").pack(side="left", padx=2)
        self.threshold_var = tk.StringVar(value="0.7")
        ttk.Entry(control_frame, textvariable=self.threshold_var, width=4).pack(
            side="left"
        )

        # Chart
        self.fig = Figure(figsize=(6, 4), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=2, pady=2)

        # Probability indicator
        gauge_frame = ttk.Frame(self)
        gauge_frame.pack(fill="x", padx=2, pady=2)

        self.probability_var = tk.StringVar(value="0%")
        self.probability_label = ttk.Label(
            gauge_frame, textvariable=self.probability_var, font=("Arial", 20, "bold")
        )
        self.probability_label.pack()

        self.progress = ttk.Progressbar(
            gauge_frame, length=150, mode="determinate", maximum=100
        )
        self.progress.pack(pady=2)

    def update_data(self):
        try:
            rates = check_mt5_data(self.symbol_var.get())
            if rates is not None:
                features, _ = self.model.prepare_data(rates)
                probability = self.model.predict_proba(features)[-1][1]

                self.update_indicators(rates, probability)

                threshold = float(self.threshold_var.get())
                if probability > threshold:
                    self.alert(probability)

        except Exception as e:
            print(f"Error updating data: {e}")

        finally:
            self.after(1000, self.update_data)

    def update_indicators(self, rates, probability):
        self.fig.clear()
        ax = self.fig.add_subplot(111)

        df = rates.tail(50)  # Display less bars for compactness
        width = 0.6
        width2 = 0.1

        up = df[df.close >= df.open]
        down = df[df.close < df.open]

        ax.bar(up.index, up.close - up.open, width, bottom=up.open, color="g")
        ax.bar(up.index, up.high - up.close, width2, bottom=up.close, color="g")
        ax.bar(up.index, up.low - up.open, width2, bottom=up.open, color="g")

        ax.bar(down.index, down.close - down.open, width, bottom=down.open, color="r")
        ax.bar(down.index, down.high - down.open, width2, bottom=down.open, color="r")
        ax.bar(down.index, down.low - down.close, width2, bottom=down.close, color="r")

        ax.grid(False)  # Remove grid for compactness
        ax.set_xticks([])  # Remove X axis labels
        self.canvas.draw()

        prob_pct = int(probability * 100)
        self.probability_var.set(f"{prob_pct}%")
        self.progress["value"] = prob_pct

        if prob_pct > 70:
            self.probability_label.configure(foreground="red")
        elif prob_pct > 50:
            self.probability_label.configure(foreground="orange")
        else:
            self.probability_label.configure(foreground="green")

    def alert(self, probability):
        window = tk.Toplevel(self)
        window.title("Alert!")
        window.geometry("200x80")  # Decreased alert window

        msg = f"High volatility: {probability:.1%}"
        ttk.Label(window, text=msg, font=("Arial", 10)).pack(pady=10)
        ttk.Button(window, text="OK", command=window.destroy).pack()


def main():
    app = VolatilityPredictor()
    app.mainloop()


if __name__ == "__main__":
    main()
