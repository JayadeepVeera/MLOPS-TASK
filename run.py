#!/usr/bin/env python3
"""
MLOps Task 0: Bitcoin Signal Generation Pipeline
Fixed for Windows UTF-8 logging issues
"""

import argparse
import sys
import logging
import yaml
import pandas as pd
import numpy as np
import json
import time
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logging(log_file):
    """Setup UTF-8 logging for Windows compatibility"""
    # Clear any existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File handler with UTF-8 encoding
    file_handler = RotatingFileHandler(
        log_file, mode='a', encoding='utf-8', maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    # Console handler with UTF-8
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Setup logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return logging.getLogger(__name__)

def load_config(config_path):
    """Load and validate config.yaml"""
    required_fields = ['seed', 'window', 'version']
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        missing = [field for field in required_fields if field not in config]
        if missing:
            raise ValueError(f"Missing required config fields: {missing}")
        
        logger.info(f"Config loaded: seed={config['seed']}, window={config['window']}, version={config['version']}")
        return config
        
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML format in {config_path}: {str(e)}")

def load_data(input_path):
    """Load and validate CSV data"""
    input_path = Path(input_path)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    file_size = input_path.stat().st_size
    if file_size == 0:
        raise ValueError("Input file is empty")
    
    try:
        df = pd.read_csv(input_path)
        logger.info(f"Loaded {len(df)} rows from {input_path}")
    except Exception as e:
        raise ValueError(f"Failed to read CSV: {str(e)}")
    
    if 'close' not in df.columns:
        raise ValueError("Required column 'close' not found in dataset")
    
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df = df.dropna(subset=['close'])
    
    logger.info(f"Validated data: {len(df)} rows with valid 'close' values")
    return df

def generate_signals(df, window, seed):
    """Generate trading signals using rolling mean"""
    np.random.seed(seed)
    
    logger.info(f"Computing rolling mean (window={window})")
    df['rolling_mean'] = df['close'].rolling(window=window).mean()
    
    logger.info("Generating signals")
    valid_mask = df['rolling_mean'].notna()
    df_valid = df[valid_mask].copy()
    df_valid['signal'] = (df_valid['close'] > df_valid['rolling_mean']).astype(int)
    
    rows_processed = len(df_valid)
    signal_rate = df_valid['signal'].mean()
    
    logger.info(f"Generated {rows_processed} signals, signal_rate={signal_rate:.4f}")
    return df_valid, rows_processed, signal_rate

def save_metrics(output_path, config, rows_processed, signal_rate, latency_ms, status="success", error_message=None):
    """Save structured metrics JSON"""
    metrics = {
        "version": config['version'],
        "rows_processed": rows_processed,
        "metric": "signal_rate",
        "value": float(signal_rate),
        "latency_ms": int(latency_ms),
        "seed": config['seed'],
        "status": status
    }
    
    if status == "error":
        metrics["error_message"] = error_message
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)
    
    print(json.dumps(metrics, indent=2))
    logger.info(f"Metrics saved to {output_path}")
    return metrics

def main():
    parser = argparse.ArgumentParser(description="MLOps Task 0: Bitcoin Signal Pipeline")
    parser.add_argument("--input", required=True, help="Input CSV file path")
    parser.add_argument("--config", required=True, help="Config YAML file path")
    parser.add_argument("--output", required=True, help="Output metrics JSON path")
    parser.add_argument("--log-file", required=True, help="Log file path")
    args = parser.parse_args()
    
    global logger
    logger = setup_logging(args.log_file)
    
    start_time = time.time()
    
    logger.info("Job started")
    try:
        config = load_config(args.config)
        np.random.seed(config['seed'])
        
        df = load_data(args.input)
        df_signals, rows_processed, signal_rate = generate_signals(df, config['window'], config['seed'])
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        logger.info("Processing completed successfully")
        logger.info(f"Final metrics: rows={rows_processed}, signal_rate={signal_rate:.4f}, latency={latency_ms}ms")
        
        save_metrics(args.output, config, rows_processed, signal_rate, latency_ms, "success")
        
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        logger.error(f"Job failed: {error_msg}")
        
        config = {'version': 'v1', 'seed': 42}
        save_metrics(args.output, config, 0, 0.0, latency_ms, "error", error_msg)
        return 1
    
    logger.info("Job completed successfully")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
