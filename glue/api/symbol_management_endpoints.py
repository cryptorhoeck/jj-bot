"""
Symbol Management API Endpoints

Allows users to:
- Add custom cryptocurrency symbols
- Remove symbols
- Enable/disable symbols for tracking
- Get list of tracked symbols
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import sqlite3
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

router = APIRouter(prefix="/api/symbols", tags=["symbol_management"])


def get_db_path() -> str:
    """Get database path"""
    return os.path.join(
        os.path.dirname(__file__), '..', '..', 'data', 'symbols.db'
    )


def init_symbols_db():
    """Initialize symbols database"""
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create symbols table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS symbols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            coingecko_id TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            custom INTEGER DEFAULT 0,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert default symbols if table is empty (verified Kraken USD pairs)
    cursor.execute("SELECT COUNT(*) FROM symbols")
    if cursor.fetchone()[0] == 0:
        # All symbols verified to exist on Kraken USD markets
        default_symbols = [
            # Major caps
            ("BTC", "bitcoin", 1, 0),
            ("ETH", "ethereum", 1, 0),
            ("SOL", "solana", 1, 0),
            ("XRP", "ripple", 1, 0),
            ("DOGE", "dogecoin", 1, 0),
            ("ADA", "cardano", 1, 0),
            ("AVAX", "avalanche-2", 1, 0),
            ("DOT", "polkadot", 1, 0),
            ("LINK", "chainlink", 1, 0),
            ("ATOM", "cosmos", 1, 0),
            # Mid caps
            ("UNI", "uniswap", 1, 0),
            ("LTC", "litecoin", 1, 0),
            ("BCH", "bitcoin-cash", 1, 0),
            ("XLM", "stellar", 1, 0),
            ("ALGO", "algorand", 1, 0),
            ("MATIC", "matic-network", 1, 0),
            ("FIL", "filecoin", 1, 0),
            ("APE", "apecoin", 1, 0),
            ("AAVE", "aave", 1, 0),
            ("CRV", "curve-dao-token", 1, 0),
            # DeFi
            ("SNX", "havven", 1, 0),
            ("GRT", "the-graph", 1, 0),
            ("COMP", "compound-governance-token", 1, 0),
            ("MKR", "maker", 1, 0),
            ("SUSHI", "sushi", 1, 0),
            ("YFI", "yearn-finance", 1, 0),
            ("1INCH", "1inch", 1, 0),
            ("LDO", "lido-dao", 1, 0),
            ("INJ", "injective-protocol", 1, 0),
            # Gaming/Metaverse
            ("SAND", "the-sandbox", 1, 0),
            ("MANA", "decentraland", 1, 0),
            ("AXS", "axie-infinity", 1, 0),
            ("ENJ", "enjincoin", 1, 0),
            ("IMX", "immutable-x", 1, 0),
            ("BLUR", "blur", 1, 0),
            # Infrastructure
            ("STORJ", "storj", 1, 0),
            ("BAT", "basic-attention-token", 1, 0),
            ("OMG", "omisego", 1, 0),
            ("FLR", "flare-networks", 1, 0),
            # Layer 1s
            ("NEAR", "near", 1, 0),
            ("FLOW", "flow", 1, 0),
            ("XTZ", "tezos", 1, 0),
            ("ETC", "ethereum-classic", 1, 0),
            ("TRX", "tron", 1, 0),
            ("KSM", "kusama", 1, 0),
            ("APT", "aptos", 1, 0),
            ("ARB", "arbitrum", 1, 0),
            ("OP", "optimism", 1, 0),
            # Privacy/Other
            ("XMR", "monero", 1, 0),
            ("SHIB", "shiba-inu", 1, 0),
            ("ZEC", "zcash", 1, 0),
            ("DASH", "dash", 1, 0),
            ("KAVA", "kava", 1, 0),
        ]

        cursor.executemany(
            "INSERT INTO symbols (symbol, coingecko_id, enabled, custom) VALUES (?, ?, ?, ?)",
            default_symbols
        )

    conn.commit()
    conn.close()


# Initialize database on import
init_symbols_db()


class SymbolAdd(BaseModel):
    symbol: str
    coingecko_id: str


class SymbolToggle(BaseModel):
    symbol: str
    enabled: bool


@router.get("/list", summary="Get All Symbols")
async def get_symbols(enabled_only: bool = False) -> Dict[str, Any]:
    """
    Get list of all symbols

    Args:
        enabled_only: If True, only return enabled symbols

    Returns:
        List of symbols with their status
    """
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()

        if enabled_only:
            cursor.execute("""
                SELECT symbol, coingecko_id, enabled, custom, added_at
                FROM symbols
                WHERE enabled = 1
                ORDER BY custom ASC, symbol ASC
            """)
        else:
            cursor.execute("""
                SELECT symbol, coingecko_id, enabled, custom, added_at
                FROM symbols
                ORDER BY custom ASC, symbol ASC
            """)

        rows = cursor.fetchall()
        conn.close()

        symbols = []
        for row in rows:
            symbols.append({
                "symbol": row[0],
                "coingecko_id": row[1],
                "enabled": bool(row[2]),
                "custom": bool(row[3]),
                "added_at": row[4]
            })

        return {
            "success": True,
            "symbols": symbols,
            "total": len(symbols)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add", summary="Add Custom Symbol")
async def add_symbol(symbol_data: SymbolAdd) -> Dict[str, Any]:
    """
    Add a custom cryptocurrency symbol

    Args:
        symbol_data: Symbol and CoinGecko ID

    Returns:
        Success status
    """
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()

        # Check if symbol already exists
        cursor.execute("SELECT symbol FROM symbols WHERE symbol = ?", (symbol_data.symbol.upper(),))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail=f"Symbol {symbol_data.symbol} already exists")

        # Add symbol
        cursor.execute("""
            INSERT INTO symbols (symbol, coingecko_id, enabled, custom)
            VALUES (?, ?, 1, 1)
        """, (symbol_data.symbol.upper(), symbol_data.coingecko_id))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": f"Symbol {symbol_data.symbol} added successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/remove/{symbol}", summary="Remove Symbol")
async def remove_symbol(symbol: str) -> Dict[str, Any]:
    """
    Remove a cryptocurrency symbol

    Args:
        symbol: Symbol to remove

    Returns:
        Success status
    """
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()

        # Check if it's a custom symbol
        cursor.execute("SELECT custom FROM symbols WHERE symbol = ?", (symbol.upper(),))
        result = cursor.fetchone()

        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")

        if not result[0]:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Cannot remove default symbol {symbol}. Disable it instead.")

        # Remove symbol
        cursor.execute("DELETE FROM symbols WHERE symbol = ?", (symbol.upper(),))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": f"Symbol {symbol} removed successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/toggle", summary="Enable/Disable Symbol")
async def toggle_symbol(toggle_data: SymbolToggle) -> Dict[str, Any]:
    """
    Enable or disable a symbol for tracking

    Args:
        toggle_data: Symbol and enabled status

    Returns:
        Success status
    """
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()

        # Check if symbol exists
        cursor.execute("SELECT symbol FROM symbols WHERE symbol = ?", (toggle_data.symbol.upper(),))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail=f"Symbol {toggle_data.symbol} not found")

        # Update enabled status
        cursor.execute("""
            UPDATE symbols
            SET enabled = ?
            WHERE symbol = ?
        """, (1 if toggle_data.enabled else 0, toggle_data.symbol.upper()))

        conn.commit()
        conn.close()

        status = "enabled" if toggle_data.enabled else "disabled"
        return {
            "success": True,
            "message": f"Symbol {toggle_data.symbol} {status} successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/enabled", summary="Get Enabled Symbols")
async def get_enabled_symbols() -> Dict[str, Any]:
    """
    Get only enabled symbols (for market feed service)

    Returns:
        List of enabled symbols with their CoinGecko IDs
    """
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()

        cursor.execute("""
            SELECT symbol, coingecko_id
            FROM symbols
            WHERE enabled = 1
            ORDER BY symbol ASC
        """)

        rows = cursor.fetchall()
        conn.close()

        # Return symbols as array (for TradingTab) AND as dict (for other services)
        symbols_list = [row[0] for row in rows]
        symbols_dict = {row[0]: row[1] for row in rows}
        coingecko_ids = [row[1] for row in rows]

        return {
            "success": True,
            "symbols": symbols_list,  # Array for TradingTab compatibility
            "symbols_map": symbols_dict,  # Dict for services that need coingecko_id
            "coingecko_ids": coingecko_ids,
            "count": len(symbols_list)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset", summary="Reset Symbols to Defaults")
async def reset_symbols() -> Dict[str, Any]:
    """
    Reset symbols database to verified Kraken defaults.
    Removes all custom symbols and restores the default list.

    Returns:
        Success status with count of symbols
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Drop and recreate the table
        cursor.execute("DROP TABLE IF EXISTS symbols")
        cursor.execute("""
            CREATE TABLE symbols (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                coingecko_id TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                custom INTEGER DEFAULT 0,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # All symbols verified to exist on Kraken USD markets
        default_symbols = [
            # Major caps
            ("BTC", "bitcoin", 1, 0),
            ("ETH", "ethereum", 1, 0),
            ("SOL", "solana", 1, 0),
            ("XRP", "ripple", 1, 0),
            ("DOGE", "dogecoin", 1, 0),
            ("ADA", "cardano", 1, 0),
            ("AVAX", "avalanche-2", 1, 0),
            ("DOT", "polkadot", 1, 0),
            ("LINK", "chainlink", 1, 0),
            ("ATOM", "cosmos", 1, 0),
            # Mid caps
            ("UNI", "uniswap", 1, 0),
            ("LTC", "litecoin", 1, 0),
            ("BCH", "bitcoin-cash", 1, 0),
            ("XLM", "stellar", 1, 0),
            ("ALGO", "algorand", 1, 0),
            ("MATIC", "matic-network", 1, 0),
            ("FIL", "filecoin", 1, 0),
            ("APE", "apecoin", 1, 0),
            ("AAVE", "aave", 1, 0),
            ("CRV", "curve-dao-token", 1, 0),
            # DeFi
            ("SNX", "havven", 1, 0),
            ("GRT", "the-graph", 1, 0),
            ("COMP", "compound-governance-token", 1, 0),
            ("MKR", "maker", 1, 0),
            ("SUSHI", "sushi", 1, 0),
            ("YFI", "yearn-finance", 1, 0),
            ("1INCH", "1inch", 1, 0),
            ("LDO", "lido-dao", 1, 0),
            ("INJ", "injective-protocol", 1, 0),
            # Gaming/Metaverse
            ("SAND", "the-sandbox", 1, 0),
            ("MANA", "decentraland", 1, 0),
            ("AXS", "axie-infinity", 1, 0),
            ("ENJ", "enjincoin", 1, 0),
            ("IMX", "immutable-x", 1, 0),
            ("BLUR", "blur", 1, 0),
            # Infrastructure
            ("STORJ", "storj", 1, 0),
            ("BAT", "basic-attention-token", 1, 0),
            ("OMG", "omisego", 1, 0),
            ("FLR", "flare-networks", 1, 0),
            # Layer 1s
            ("NEAR", "near", 1, 0),
            ("FLOW", "flow", 1, 0),
            ("XTZ", "tezos", 1, 0),
            ("ETC", "ethereum-classic", 1, 0),
            ("TRX", "tron", 1, 0),
            ("KSM", "kusama", 1, 0),
            ("APT", "aptos", 1, 0),
            ("ARB", "arbitrum", 1, 0),
            ("OP", "optimism", 1, 0),
            # Privacy/Other
            ("XMR", "monero", 1, 0),
            ("SHIB", "shiba-inu", 1, 0),
            ("ZEC", "zcash", 1, 0),
            ("DASH", "dash", 1, 0),
            ("KAVA", "kava", 1, 0),
        ]

        cursor.executemany(
            "INSERT INTO symbols (symbol, coingecko_id, enabled, custom) VALUES (?, ?, ?, ?)",
            default_symbols
        )

        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": f"Symbols reset to {len(default_symbols)} verified Kraken defaults",
            "count": len(default_symbols)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
