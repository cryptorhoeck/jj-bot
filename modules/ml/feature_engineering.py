"""
ML Feature Engineering Module

Extracts and engineers features from market data for machine learning applications

Features include:
- Price-based features (returns, momentum, volatility)
- Technical indicator features (RSI, MACD, Bollinger Bands, etc.)
- Volume-based features
- Time-based features (day of week, hour, etc.)
- Market regime features
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.analysis import indicators


class FeatureEngineer:
    """Extract and engineer features from OHLCV data"""

    def __init__(self):
        self.indicators = indicators

    def extract_all_features(self, candles: List[Dict], include_labels: bool = False) -> Dict:
        """
        Extract comprehensive feature set from OHLCV candles

        Args:
            candles: List of OHLCV candles with keys: time, open, high, low, close, volume
            include_labels: If True, also generate labels for supervised learning

        Returns:
            Dict with:
                - features: List of feature vectors (one per candle)
                - feature_names: List of feature names
                - labels: Optional list of labels (next candle direction)
                - metadata: Additional information
        """
        if not candles or len(candles) < 50:
            return {
                "success": False,
                "error": "Insufficient data (need at least 50 candles)"
            }

        # Extract price arrays
        close_prices = [c["close"] for c in candles]
        high_prices = [c["high"] for c in candles]
        low_prices = [c["low"] for c in candles]
        open_prices = [c["open"] for c in candles]
        volumes = [c.get("volume", 0) for c in candles]
        timestamps = [c["time"] for c in candles]

        # Initialize feature arrays
        all_features = []
        feature_names = []

        # 1. Price-based features
        price_features, price_feature_names = self._extract_price_features(
            open_prices, high_prices, low_prices, close_prices
        )

        # 2. Technical indicator features
        indicator_features, indicator_feature_names = self._extract_indicator_features(
            high_prices, low_prices, close_prices, volumes
        )

        # 3. Volume features
        volume_features, volume_feature_names = self._extract_volume_features(volumes, close_prices)

        # 4. Time-based features
        time_features, time_feature_names = self._extract_time_features(timestamps)

        # 5. Market regime features
        regime_features, regime_feature_names = self._extract_market_regime_features(
            close_prices, high_prices, low_prices, volumes
        )

        # Combine all features
        num_samples = len(candles)

        for i in range(num_samples):
            feature_vector = []

            # Add price features
            if price_features and i < len(price_features):
                feature_vector.extend(price_features[i])

            # Add indicator features
            if indicator_features and i < len(indicator_features):
                feature_vector.extend(indicator_features[i])

            # Add volume features
            if volume_features and i < len(volume_features):
                feature_vector.extend(volume_features[i])

            # Add time features
            if time_features and i < len(time_features):
                feature_vector.extend(time_features[i])

            # Add regime features
            if regime_features and i < len(regime_features):
                feature_vector.extend(regime_features[i])

            all_features.append(feature_vector)

        # Combine feature names
        feature_names = (
            price_feature_names +
            indicator_feature_names +
            volume_feature_names +
            time_feature_names +
            regime_feature_names
        )

        result = {
            "success": True,
            "features": all_features,
            "feature_names": feature_names,
            "num_features": len(feature_names),
            "num_samples": len(all_features)
        }

        # Generate labels if requested
        if include_labels:
            labels = self._generate_labels(close_prices)
            result["labels"] = labels
            result["label_distribution"] = {
                "up": labels.count(1),
                "down": labels.count(-1),
                "neutral": labels.count(0)
            }

        return result

    def _extract_price_features(
        self,
        open_prices: List[float],
        high_prices: List[float],
        low_prices: List[float],
        close_prices: List[float]
    ) -> Tuple[List[List[float]], List[str]]:
        """Extract price-based features"""

        features = []
        feature_names = [
            "return_1",          # 1-period return
            "return_5",          # 5-period return
            "return_10",         # 10-period return
            "return_20",         # 20-period return
            "log_return_1",      # Log return
            "hl_range",          # High-low range
            "oc_range",          # Open-close range
            "price_position",    # Close position in HL range
            "gap",               # Gap from previous close
            "momentum_5",        # 5-period momentum
            "momentum_10",       # 10-period momentum
            "volatility_10",     # 10-period volatility
            "volatility_20"      # 20-period volatility
        ]

        for i in range(len(close_prices)):
            feature_vec = []

            # Returns
            if i >= 1:
                feature_vec.append((close_prices[i] - close_prices[i-1]) / close_prices[i-1])
                feature_vec.append(np.log(close_prices[i] / close_prices[i-1]))
            else:
                feature_vec.extend([0, 0])

            if i >= 5:
                feature_vec.append((close_prices[i] - close_prices[i-5]) / close_prices[i-5])
            else:
                feature_vec.append(0)

            if i >= 10:
                feature_vec.append((close_prices[i] - close_prices[i-10]) / close_prices[i-10])
            else:
                feature_vec.append(0)

            if i >= 20:
                feature_vec.append((close_prices[i] - close_prices[i-20]) / close_prices[i-20])
            else:
                feature_vec.append(0)

            # Price ranges
            hl_range = (high_prices[i] - low_prices[i]) / close_prices[i] if close_prices[i] > 0 else 0
            oc_range = (close_prices[i] - open_prices[i]) / close_prices[i] if close_prices[i] > 0 else 0
            price_position = ((close_prices[i] - low_prices[i]) / (high_prices[i] - low_prices[i])
                            if high_prices[i] > low_prices[i] else 0.5)

            feature_vec.extend([hl_range, oc_range, price_position])

            # Gap
            gap = ((open_prices[i] - close_prices[i-1]) / close_prices[i-1]
                  if i >= 1 and close_prices[i-1] > 0 else 0)
            feature_vec.append(gap)

            # Momentum
            if i >= 5:
                momentum_5 = close_prices[i] - close_prices[i-5]
            else:
                momentum_5 = 0
            feature_vec.append(momentum_5)

            if i >= 10:
                momentum_10 = close_prices[i] - close_prices[i-10]
            else:
                momentum_10 = 0
            feature_vec.append(momentum_10)

            # Volatility (standard deviation of returns)
            if i >= 10:
                returns_10 = [(close_prices[j] - close_prices[j-1]) / close_prices[j-1]
                             for j in range(i-9, i+1) if j > 0]
                volatility_10 = np.std(returns_10) if returns_10 else 0
            else:
                volatility_10 = 0
            feature_vec.append(volatility_10)

            if i >= 20:
                returns_20 = [(close_prices[j] - close_prices[j-1]) / close_prices[j-1]
                             for j in range(i-19, i+1) if j > 0]
                volatility_20 = np.std(returns_20) if returns_20 else 0
            else:
                volatility_20 = 0
            feature_vec.append(volatility_20)

            features.append(feature_vec)

        return features, feature_names

    def _extract_indicator_features(
        self,
        high_prices: List[float],
        low_prices: List[float],
        close_prices: List[float],
        volumes: List[float]
    ) -> Tuple[List[List[float]], List[str]]:
        """Extract technical indicator features"""

        feature_names = [
            "rsi_14",
            "rsi_normalized",
            "sma_20",
            "sma_50",
            "price_to_sma20",
            "price_to_sma50",
            "sma20_to_sma50",
            "macd",
            "macd_signal",
            "macd_histogram",
            "bb_upper",
            "bb_middle",
            "bb_lower",
            "bb_width",
            "bb_position",
            "atr_14"
        ]

        # Calculate indicators
        rsi = self.indicators.rsi(close_prices, 14)
        sma_20 = self.indicators.sma(close_prices, 20)
        sma_50 = self.indicators.sma(close_prices, 50)
        macd_data = self.indicators.macd(close_prices)
        bb_data = self.indicators.bollinger_bands(close_prices, 20, 2.0)
        atr = self.indicators.atr(high_prices, low_prices, close_prices, 14)

        features = []

        for i in range(len(close_prices)):
            feature_vec = []

            # RSI
            rsi_val = rsi[i] if rsi[i] is not None else 50
            feature_vec.append(rsi_val)
            feature_vec.append((rsi_val - 50) / 50)  # Normalized RSI

            # Moving averages
            sma20_val = sma_20[i] if sma_20[i] is not None else close_prices[i]
            sma50_val = sma_50[i] if sma_50[i] is not None else close_prices[i]

            feature_vec.append(sma20_val)
            feature_vec.append(sma50_val)

            # Price to MA ratios
            price_to_sma20 = (close_prices[i] - sma20_val) / sma20_val if sma20_val > 0 else 0
            price_to_sma50 = (close_prices[i] - sma50_val) / sma50_val if sma50_val > 0 else 0
            sma20_to_sma50 = (sma20_val - sma50_val) / sma50_val if sma50_val > 0 else 0

            feature_vec.extend([price_to_sma20, price_to_sma50, sma20_to_sma50])

            # MACD
            macd_val = macd_data["macd_line"][i] if macd_data["macd_line"][i] is not None else 0
            signal_val = macd_data["signal_line"][i] if macd_data["signal_line"][i] is not None else 0
            histogram_val = macd_data["histogram"][i] if macd_data["histogram"][i] is not None else 0

            feature_vec.extend([macd_val, signal_val, histogram_val])

            # Bollinger Bands
            bb_upper = bb_data["upper_band"][i] if bb_data["upper_band"][i] is not None else close_prices[i]
            bb_middle = bb_data["middle_band"][i] if bb_data["middle_band"][i] is not None else close_prices[i]
            bb_lower = bb_data["lower_band"][i] if bb_data["lower_band"][i] is not None else close_prices[i]
            bb_width = (bb_upper - bb_lower) / bb_middle if bb_middle > 0 else 0
            bb_position = ((close_prices[i] - bb_lower) / (bb_upper - bb_lower)
                          if bb_upper > bb_lower else 0.5)

            feature_vec.extend([bb_upper, bb_middle, bb_lower, bb_width, bb_position])

            # ATR
            atr_val = atr[i] if atr[i] is not None else 0
            feature_vec.append(atr_val)

            features.append(feature_vec)

        return features, feature_names

    def _extract_volume_features(
        self,
        volumes: List[float],
        close_prices: List[float]
    ) -> Tuple[List[List[float]], List[str]]:
        """Extract volume-based features"""

        feature_names = [
            "volume",
            "volume_sma_20",
            "volume_ratio",
            "volume_change",
            "price_volume_trend"
        ]

        # Calculate volume moving average
        volume_sma = self.indicators.sma(volumes, 20)

        features = []

        for i in range(len(volumes)):
            feature_vec = []

            vol = volumes[i]
            vol_sma = volume_sma[i] if volume_sma[i] is not None else vol

            feature_vec.append(vol)
            feature_vec.append(vol_sma)

            # Volume ratio (current / average)
            vol_ratio = vol / vol_sma if vol_sma > 0 else 1
            feature_vec.append(vol_ratio)

            # Volume change
            vol_change = ((vol - volumes[i-1]) / volumes[i-1]
                         if i > 0 and volumes[i-1] > 0 else 0)
            feature_vec.append(vol_change)

            # Price-volume trend
            pvt = (vol * ((close_prices[i] - close_prices[i-1]) / close_prices[i-1])
                  if i > 0 and close_prices[i-1] > 0 else 0)
            feature_vec.append(pvt)

            features.append(feature_vec)

        return features, feature_names

    def _extract_time_features(self, timestamps: List[int]) -> Tuple[List[List[float]], List[str]]:
        """Extract time-based features"""

        feature_names = [
            "hour",
            "day_of_week",
            "day_of_month",
            "month",
            "is_weekend",
            "hour_sin",
            "hour_cos",
            "dow_sin",
            "dow_cos"
        ]

        features = []

        for ts in timestamps:
            dt = datetime.fromtimestamp(ts)

            hour = dt.hour
            day_of_week = dt.weekday()
            day_of_month = dt.day
            month = dt.month
            is_weekend = 1 if day_of_week >= 5 else 0

            # Cyclical encoding for hour and day of week
            hour_sin = np.sin(2 * np.pi * hour / 24)
            hour_cos = np.cos(2 * np.pi * hour / 24)
            dow_sin = np.sin(2 * np.pi * day_of_week / 7)
            dow_cos = np.cos(2 * np.pi * day_of_week / 7)

            features.append([
                hour, day_of_week, day_of_month, month, is_weekend,
                hour_sin, hour_cos, dow_sin, dow_cos
            ])

        return features, feature_names

    def _extract_market_regime_features(
        self,
        close_prices: List[float],
        high_prices: List[float],
        low_prices: List[float],
        volumes: List[float]
    ) -> Tuple[List[List[float]], List[str]]:
        """Extract market regime features"""

        feature_names = [
            "trend_strength",
            "volatility_regime",
            "volume_regime",
            "market_phase"
        ]

        features = []

        for i in range(len(close_prices)):
            feature_vec = []

            # Trend strength (using 20-period linear regression slope)
            if i >= 20:
                period_prices = close_prices[i-19:i+1]
                x = np.arange(len(period_prices))
                coeffs = np.polyfit(x, period_prices, 1)
                trend_strength = coeffs[0] / np.mean(period_prices) if np.mean(period_prices) > 0 else 0
            else:
                trend_strength = 0
            feature_vec.append(trend_strength)

            # Volatility regime (high/medium/low based on recent ATR)
            if i >= 14:
                recent_ranges = [(high_prices[j] - low_prices[j]) / close_prices[j]
                               for j in range(i-13, i+1) if close_prices[j] > 0]
                avg_range = np.mean(recent_ranges) if recent_ranges else 0
                volatility_regime = 2 if avg_range > 0.03 else (1 if avg_range > 0.015 else 0)
            else:
                volatility_regime = 1
            feature_vec.append(volatility_regime)

            # Volume regime
            if i >= 20:
                recent_volumes = volumes[i-19:i+1]
                avg_vol = np.mean(recent_volumes)
                volume_regime = 2 if volumes[i] > avg_vol * 1.5 else (1 if volumes[i] > avg_vol else 0)
            else:
                volume_regime = 1
            feature_vec.append(volume_regime)

            # Market phase (0=accumulation, 1=markup, 2=distribution, 3=markdown)
            if i >= 20:
                # Simple heuristic based on price and volume trends
                price_trend = 1 if close_prices[i] > np.mean(close_prices[i-19:i+1]) else 0
                volume_trend = 1 if volumes[i] > np.mean(volumes[i-19:i+1]) else 0

                if price_trend and volume_trend:
                    phase = 1  # Markup
                elif not price_trend and volume_trend:
                    phase = 3  # Markdown
                elif price_trend and not volume_trend:
                    phase = 2  # Distribution
                else:
                    phase = 0  # Accumulation
            else:
                phase = 0
            feature_vec.append(phase)

            features.append(feature_vec)

        return features, feature_names

    def _generate_labels(self, close_prices: List[float]) -> List[int]:
        """
        Generate labels for supervised learning

        Returns:
            List of labels: 1 (up), -1 (down), 0 (neutral)
        """
        labels = []

        for i in range(len(close_prices)):
            if i < len(close_prices) - 1:
                # Look at next candle
                next_price = close_prices[i + 1]
                current_price = close_prices[i]

                change_pct = ((next_price - current_price) / current_price) * 100

                # Threshold for significance
                threshold = 0.5

                if change_pct > threshold:
                    labels.append(1)  # Up
                elif change_pct < -threshold:
                    labels.append(-1)  # Down
                else:
                    labels.append(0)  # Neutral
            else:
                # Last candle has no next candle
                labels.append(0)

        return labels

    def normalize_features(
        self,
        features: List[List[float]],
        method: str = "standardize"
    ) -> Tuple[List[List[float]], Dict]:
        """
        Normalize feature vectors

        Args:
            features: List of feature vectors
            method: "standardize" (z-score) or "minmax" (0-1 scaling)

        Returns:
            Tuple of (normalized_features, normalization_params)
        """
        if not features:
            return features, {}

        features_array = np.array(features)
        num_features = features_array.shape[1]

        normalized = np.zeros_like(features_array)
        params = {}

        if method == "standardize":
            # Z-score normalization
            for i in range(num_features):
                col = features_array[:, i]
                mean = np.mean(col)
                std = np.std(col)

                if std > 0:
                    normalized[:, i] = (col - mean) / std
                else:
                    normalized[:, i] = col

                params[f"feature_{i}"] = {"mean": mean, "std": std}

        elif method == "minmax":
            # Min-max normalization
            for i in range(num_features):
                col = features_array[:, i]
                min_val = np.min(col)
                max_val = np.max(col)

                if max_val > min_val:
                    normalized[:, i] = (col - min_val) / (max_val - min_val)
                else:
                    normalized[:, i] = col

                params[f"feature_{i}"] = {"min": min_val, "max": max_val}

        return normalized.tolist(), {"method": method, "params": params}


# Singleton instance
feature_engineer = FeatureEngineer()
