function TradesTable({ trades }) {
  return (
    <div className="p-4 bg-white rounded-xl shadow">
      <h2 className="text-xl font-semibold mb-4">📋 Recent Trades</h2>
      {trades.length === 0 ? (
        <p className="text-gray-500">No trades yet...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border">
            <thead>
              <tr className="bg-gray-100">
                <th className="p-2 border">Time</th>
                <th className="p-2 border">Symbol</th>
                <th className="p-2 border">Signal</th>
                <th className="p-2 border">Price</th>
                <th className="p-2 border">VWAP</th>
                <th className="p-2 border">P&L</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade, i) => (
                <tr key={i} className="border-t hover:bg-gray-50">
                  <td className="p-2 border">{trade.timestamp}</td>
                  <td className="p-2 border">{trade.symbol}</td>
                  <td className={`p-2 border font-bold ${
                    trade.signal === "LONG" ? "text-green-600" : "text-red-600"
                  }`}>
                    {trade.signal}
                  </td>
                  <td className="p-2 border font-mono">${trade.last_price}</td>
                  <td className="p-2 border font-mono">${trade.vwap}</td>
                  <td className={`p-2 border font-bold ${
                    trade.pnl >= 0 ? "text-green-600" : "text-red-600"
                  }`}>
                    ${trade.pnl?.toFixed(2) || "0.00"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default TradesTable;
