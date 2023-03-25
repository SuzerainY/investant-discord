import yfinance as yf

class Holding:
    def __init__(self, ticker: str, quantity: int, avgCost: float, totalCost: float):
        self.ticker = ticker.upper()
        self.quantity = quantity
        self.avgCost = round(avgCost, 8)
        self.totalCost = round(totalCost, 2)

class Portfolio:
    def __init__(self, Owner: str, CashBalance: float = 50000.00, Holdings: list[Holding] = []):
        self.owner = Owner.upper()
        self.cashBalance = round(CashBalance, 2)
        self.holdings = Holdings
    
    def buy(self, Holding: Holding):
        self.holdings.append(Holding)

    def sell(self, ticker: str, quantity: int, onMargin: bool = False):
        ticker = ticker.upper()
        tickerFound = False
        for holding in self.holdings:
            if holding.ticker == ticker: # We already have this position
                tickerFound = True

                if not onMargin: # Not trading on margin
                    if holding.quantity - quantity < 0:
                        print(f"You do not own {quantity} shares of {ticker}. You currently hold {holding.quantity}. No transaction processed.")
                        return
                    
                    elif holding.quantity - quantity == 0: # Perfect closing of position
                        stock = yf.Ticker(ticker)
                        sharePrice = round(stock.history().tail(1)['Close'][0], 2)
                        self.cashBalance += round(sharePrice * quantity, 2)
                        self.holdings.remove(holding)
                        print(f"Position closed. Your new cash balance is {self.cashBalance}.")
                        return

                    else:
                        stock = yf.Ticker(ticker)
                        sharePrice = round(stock.history().tail(1)['Close'][0], 2)
                        holding.quantity -= quantity
                        holding.totalCost -= round(quantity * holding.avgCost, 2)
                        self.cashBalance += round(sharePrice * quantity, 2)
                        print(f"Sell Transaction Processed. You now have {holding.quantity} shares of {ticker}. Your new cash balance is {self.cashBalance}.")
                        return
            
        if not tickerFound:
            if not onMargin: # They don't want to go short, don't process
                print(f"I'm sorry. We don't have it in our records that you own {ticker}.")
                return

        
RyanPortfolio = Portfolio(Owner = "Ryan")
RyanPortfolio.sell(ticker = "AMZN", quantity = 20)