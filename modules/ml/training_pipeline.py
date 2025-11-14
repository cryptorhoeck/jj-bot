"""
ML Training Pipeline

Automated pipeline for training and evaluating ML models
"""

import sys
import os
import asyncio
from typing import Dict, List, Optional, Any

# Add paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.ml.model_trainer import ModelTrainer
from modules.data.cached_market_data_service import cached_market_data_service


class TrainingPipeline:
    """Automated pipeline for model training"""

    def __init__(self, models_dir: str = "./data/ml_models"):
        """
        Initialize training pipeline

        Args:
            models_dir: Directory to save trained models
        """
        self.trainer = ModelTrainer(models_dir=models_dir)
        self.market_service = cached_market_data_service

    def fetch_training_data(
        self,
        symbol: str,
        timeframe: str = '1h',
        num_candles: int = 5000,
        source: str = 'auto'
    ) -> List[Dict]:
        """
        Fetch training data from market data service

        Args:
            symbol: Trading symbol (e.g., 'BTC', 'ETH')
            timeframe: Candle timeframe
            num_candles: Number of candles to fetch
            source: Data source ('kraken', 'yahoo', or 'auto')

        Returns:
            List of OHLCV candles
        """
        print(f"📊 Fetching training data for {symbol}...")
        print(f"   Timeframe: {timeframe}")
        print(f"   Candles:   {num_candles}")

        result = self.market_service.get_ohlcv(
            symbol=symbol,
            source=source,
            timeframe=timeframe,
            num_candles=num_candles
        )

        if not result['success']:
            raise ValueError(f"Failed to fetch data: {result.get('error', 'Unknown error')}")

        candles = result['candles']
        print(f"✅ Fetched {len(candles)} candles from {result['source']}")

        return candles

    def run_training(
        self,
        symbol: str,
        model_type: str = 'random_forest',
        timeframe: str = '1h',
        num_candles: int = 5000,
        source: str = 'auto',
        test_size: float = 0.2,
        save_model: bool = True,
        model_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Run complete training pipeline

        Args:
            symbol: Trading symbol
            model_type: 'random_forest' or 'xgboost'
            timeframe: Candle timeframe
            num_candles: Number of candles for training
            source: Data source
            test_size: Proportion of data for testing
            save_model: Whether to save the trained model
            model_params: Additional model parameters

        Returns:
            Training results dictionary
        """
        print("=" * 60)
        print("ML TRAINING PIPELINE")
        print("=" * 60)

        try:
            # Fetch training data
            candles = self.fetch_training_data(
                symbol=symbol,
                timeframe=timeframe,
                num_candles=num_candles,
                source=source
            )

            if len(candles) < 100:
                return {
                    'success': False,
                    'error': f'Insufficient data: {len(candles)} candles (need at least 100)'
                }

            # Prepare data
            print(f"\n🔧 Preparing training data...")
            X_train, X_test, y_train, y_test = self.trainer.prepare_training_data(
                candles,
                test_size=test_size,
                normalize=True
            )

            print(f"   Training samples: {len(X_train)}")
            print(f"   Test samples:     {len(X_test)}")
            print(f"   Features:         {X_train.shape[1]}")

            # Train model
            print(f"\n🎯 Training {model_type} model...")

            params = model_params or {}

            if model_type == 'random_forest':
                train_result = self.trainer.train_random_forest(
                    X_train, y_train,
                    n_estimators=params.get('n_estimators', 100),
                    max_depth=params.get('max_depth', 10),
                    min_samples_split=params.get('min_samples_split', 5)
                )
            elif model_type == 'xgboost':
                train_result = self.trainer.train_xgboost(
                    X_train, y_train,
                    n_estimators=params.get('n_estimators', 100),
                    max_depth=params.get('max_depth', 6),
                    learning_rate=params.get('learning_rate', 0.1)
                )
            else:
                return {
                    'success': False,
                    'error': f"Unknown model type: {model_type}"
                }

            if not train_result['success']:
                return train_result

            print(f"   ✅ Training completed")
            if 'cv_mean_accuracy' in train_result:
                print(f"   CV Accuracy: {train_result['cv_mean_accuracy']:.4f} ± {train_result['cv_std_accuracy']:.4f}")

            # Evaluate model
            print(f"\n📈 Evaluating model on test set...")
            eval_result = self.trainer.evaluate(X_test, y_test)

            if not eval_result['success']:
                return eval_result

            # Print top features
            if eval_result.get('feature_importance'):
                print(f"\n🎯 Top 10 Important Features:")
                for i, feat in enumerate(eval_result['feature_importance'][:10], 1):
                    print(f"   {i:2d}. {feat['feature']:30s} {feat['importance']:.4f}")

            # Save model
            if save_model:
                print(f"\n💾 Saving model...")
                model_name = f"{symbol}_{timeframe}_{model_type}"
                metadata = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'num_candles': num_candles,
                    'source': source,
                    'data_source': result.get('source', 'unknown')
                }

                save_result = self.trainer.save_model(model_name, metadata)

                if save_result['success']:
                    print(f"   ✅ Model saved: {save_result['model_file']}")
                else:
                    print(f"   ⚠️ Failed to save model: {save_result.get('error')}")

            print("\n" + "=" * 60)
            print("TRAINING COMPLETED SUCCESSFULLY")
            print("=" * 60)

            return {
                'success': True,
                'symbol': symbol,
                'model_type': model_type,
                'timeframe': timeframe,
                'training': train_result,
                'evaluation': eval_result,
                'save_result': save_result if save_model else None,
                'trainer': self.trainer
            }

        except Exception as e:
            print(f"\n❌ Training failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def batch_train(
        self,
        symbols: List[str],
        model_type: str = 'random_forest',
        timeframe: str = '1h',
        **kwargs
    ) -> Dict[str, Any]:
        """
        Train models for multiple symbols

        Args:
            symbols: List of trading symbols
            model_type: Model type to train
            timeframe: Candle timeframe
            **kwargs: Additional training parameters

        Returns:
            Batch training results
        """
        results = {}

        for symbol in symbols:
            print(f"\n\n{'='*60}")
            print(f"Training model for {symbol}")
            print(f"{'='*60}\n")

            result = self.run_training(
                symbol=symbol,
                model_type=model_type,
                timeframe=timeframe,
                **kwargs
            )

            results[symbol] = result

        # Summary
        print("\n\n" + "=" * 60)
        print("BATCH TRAINING SUMMARY")
        print("=" * 60)

        successful = sum(1 for r in results.values() if r['success'])
        print(f"Total symbols: {len(symbols)}")
        print(f"Successful:    {successful}")
        print(f"Failed:        {len(symbols) - successful}")

        print("\nResults:")
        for symbol, result in results.items():
            if result['success']:
                acc = result['evaluation']['accuracy']
                print(f"  ✅ {symbol}: Accuracy = {acc:.4f}")
            else:
                error = result.get('error', 'Unknown error')
                print(f"  ❌ {symbol}: {error}")

        return {
            'success': True,
            'results': results,
            'summary': {
                'total': len(symbols),
                'successful': successful,
                'failed': len(symbols) - successful
            }
        }


# Main execution
async def main():
    """Run training pipeline from command line"""
    import argparse

    parser = argparse.ArgumentParser(description='Train ML models for price prediction')
    parser.add_argument('--symbol', '-s', type=str, default='BTC', help='Trading symbol')
    parser.add_argument('--model', '-m', type=str, default='random_forest',
                        choices=['random_forest', 'xgboost'],
                        help='Model type')
    parser.add_argument('--timeframe', '-t', type=str, default='1h', help='Timeframe')
    parser.add_argument('--candles', '-n', type=int, default=5000, help='Number of candles')
    parser.add_argument('--source', type=str, default='auto', help='Data source')
    parser.add_argument('--test-size', type=float, default=0.2, help='Test set proportion')
    parser.add_argument('--n-estimators', type=int, default=100, help='Number of estimators')
    parser.add_argument('--max-depth', type=int, default=10, help='Maximum tree depth')
    parser.add_argument('--no-save', action='store_true', help='Do not save model')
    parser.add_argument('--batch', nargs='+', help='Train multiple symbols')

    args = parser.parse_args()

    pipeline = TrainingPipeline()

    # Batch training
    if args.batch:
        result = pipeline.batch_train(
            symbols=args.batch,
            model_type=args.model,
            timeframe=args.timeframe,
            num_candles=args.candles,
            source=args.source,
            test_size=args.test_size,
            save_model=not args.no_save,
            model_params={
                'n_estimators': args.n_estimators,
                'max_depth': args.max_depth
            }
        )
    # Single symbol training
    else:
        result = pipeline.run_training(
            symbol=args.symbol,
            model_type=args.model,
            timeframe=args.timeframe,
            num_candles=args.candles,
            source=args.source,
            test_size=args.test_size,
            save_model=not args.no_save,
            model_params={
                'n_estimators': args.n_estimators,
                'max_depth': args.max_depth
            }
        )

    if not result['success']:
        print(f"\n❌ Training failed: {result.get('error')}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
