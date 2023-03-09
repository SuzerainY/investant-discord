# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# region IMPORTS

from PaperTradeEmbeds import *
import yfinance as yf
import yahooquery as yq
import numpy as np
import interactions
import interactions.ext.files
from bisect import bisect_left

# endregion IMPORTS
# ------------------------------------------------------------------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# region MISCELLANEOUS

# Binary Search
def BinarySearch(List: list, Value: str):
    i = bisect_left(List, Value) # returns the index of the value searched
    return i != len(List) and List[i] == Value # returns True if found, False if not

# Generate news articles about an equity
def TGetNews(ticker):
    stock = yf.Ticker(ticker)
    TickerNews = f"**{ticker} News:**\n\n"
    for Article in stock.news:
        TickerNews += f"{Article['title']}: {Article['link']}\n"
    return TickerNews

# endregion MISCELLANEOUS
# ------------------------------------------------------------------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# region MAIN COMMAND METHODS CONSOLIDATED

# /portfolio MAIN METHOD
async def MainPortfolioMethod(ctx, PaperTradeDB, UserID, UserSeesOnly, Gold: bool):
    # Grab User's cash balance
    DBCursor = PaperTradeDB.cursor() # Open Cursor
    DBCursor.execute("SELECT TotalCost FROM PortfolioHoldings WHERE UserID = %s AND Holding = %s", (str(UserID), "Cash Balance")) # Fetch User's Cash Balance
    UserCashBalance = DBCursor.fetchone()[0]

    # Grab User's total cash proceeds
    DBCursor.execute("SELECT TotalCost FROM PortfolioHoldings WHERE UserID = %s AND Holding = %s", (str(UserID), "Cash Proceeds")) # Fetch User's Cash Proceeds
    UserCashProceeds = DBCursor.fetchone()[0]

    # Grab User's portfolio positions other than cash
    DBCursor.execute("SELECT * FROM PortfolioHoldings WHERE UserID = %s AND Holding != %s AND Holding != %s", (str(UserID), "Cash Balance", "Cash Proceeds"))
    Positions = DBCursor.fetchall()

    # Grab User's Banking positions
    DBCursor.execute("SELECT Checking, Savings FROM BankingAccounts WHERE UserID = %s", [str(UserID)])
    BankAccounts = DBCursor.fetchone()
    UserChecking = BankAccounts[0]
    UserSavings = BankAccounts[1]

    # Done interacting with database
    DBCursor.close() # Close Cursor

    embed, files = GeneratePortfolioEmbed(Positions, UserCashBalance, UserCashProceeds, UserChecking, UserSavings, Gold)
    await ctx.send(embeds = embed, files = files, ephemeral = UserSeesOnly)
    return

# /buy MAIN METHOD
async def BuyMainMethod(ctx, PaperTradeBot, UserSeesOnly, PaperTradeDB, GuildMember, UserID, InvestantServerID, CashFlow, InvestantTotalMoneyMarketFund, PaperTrade, PaperTradeGold, quantity, ticker, itmm):
    # Require variables: what stock, what price
    ticker = ticker.upper()
    stock = yf.Ticker(ticker)
    price = round(stock.history().tail(1)['Close'][0], 2)

    # If price = $0.00, they could buy infinite shares, so we don't allow
    if price == 0:
        await ctx.send(f"This equity is priced at ${price:,.2f}. We don't buy worthless assets here.", ephemeral = UserSeesOnly)
        return

    cost = round(price * quantity, 2) # cost of transaction

    # If this is a personal transaction, then proceed
    if not itmm:
        # Make sure they didn't send in ITMM Channel
        if ctx.channel.id == InvestantTotalMoneyMarketFund:
            await ctx.send(f"This command is restricted to <#{PaperTrade}> and <#{PaperTradeGold}>.", ephemeral = UserSeesOnly)
            return

        # Check if user already has [20] securities in their portfolio
        DBCursor = PaperTradeDB.cursor() # Open Cursor
        DBCursor.execute("SELECT COUNT(Holding) FROM PortfolioHoldings WHERE UserID = %s AND Holding != %s AND Holding != %s", (str(UserID), "Cash Balance", "Cash Proceeds"))
        UserHoldingsCount = DBCursor.fetchone()[0]
        if UserHoldingsCount >= 20:
            DBCursor.close() # Close Cursor
            await ctx.send(f"I'm sorry, <@{UserID}>, you currently have {UserHoldingsCount} open positions and have reached our allowed limit.\nAs Investant grows, we will upgrade database and server size to allow for more complex portfolios with even more open positions.", ephemeral = UserSeesOnly)
            return

        # Grab User's cash balance
        DBCursor.execute("SELECT TotalCost FROM PortfolioHoldings WHERE UserID = %s AND Holding = %s", (str(UserID), "Cash Balance")) # Fetch User's Cash Balance
        UserCashBalance = DBCursor.fetchone()[0]

        if cost > UserCashBalance: # User attempted to purchase more than they could afford
            DBCursor.close() # Close Cursor
            await ctx.send(f"Insufficient Funds. I'm sorry, {GuildMember.name}, your current portfolio cash balance is ${UserCashBalance:,.2f}.", ephemeral = UserSeesOnly)
            return

        # Check if user already owns this equity
        DBCursor.execute("SELECT Quantity, AvgCost, TotalCost FROM PortfolioHoldings WHERE UserID = %s AND Holding = %s", (str(UserID), ticker)) # We only need Quantity and AvgCost for calcs, so grab them if they exist
        Result = DBCursor.fetchall()

        # Purchase will execute, so prepare CashFlowChannel
        CashFlowChannel = await interactions.get(PaperTradeBot, interactions.Channel, object_id = CashFlow)

        if len(Result) > 0: # If ticker is already in portfolio, purchase more shares

            # Gather previous data from User's position and prepare new data for deployment
            CurrentQuantity, CurrentAvgCost, CurrentTotalCost = Result[0][0], Result[0][1], Result[0][2]
            NewQuantity = CurrentQuantity + quantity
            NewAvgCost = round(((CurrentAvgCost * CurrentQuantity) + cost) / (NewQuantity), 7)
            NewTotalCost = round(CurrentTotalCost + cost, 2)

            # Insert new data about position after buy transaction
            DBCursor.execute("UPDATE PortfolioHoldings SET Quantity = %s, AvgCost = %s, TotalCost = %s WHERE UserID = %s AND Holding = %s", (NewQuantity, NewAvgCost, NewTotalCost, str(UserID), ticker))
            
            # Update User's new Cash Balance
            NewCashBalance = round(UserCashBalance - cost, 2)
            DBCursor.execute("UPDATE PortfolioHoldings SET TotalCost = %s WHERE UserID = %s AND Holding = %s", (NewCashBalance, str(UserID), "Cash Balance"))

        else: # If ticker not in portfolio, add it to the portfolio

            # Insert data about User's new position
            DBCursor.execute("INSERT INTO PortfolioHoldings (UserID, Holding, Quantity, AvgCost, TotalCost) VALUES (%s, %s, %s, %s, %s)", (str(UserID), ticker, quantity, price, cost))
            # Update User's Cash Balance
            NewCashBalance = round(UserCashBalance - cost, 2)
            DBCursor.execute("UPDATE PortfolioHoldings SET TotalCost = %s WHERE UserID = %s AND Holding = %s", (NewCashBalance, str(UserID), "Cash Balance"))

        # Commit these changes to the database
        PaperTradeDB.commit()
        DBCursor.close() # Close Cursor

        # Send message to PaperTrade channel and Cash Flow channel
        await ctx.send(f"<@{UserID}> bought {quantity} shares of {ticker} for ${cost:,.2f} at ${price:,.2f} per share")
        await CashFlowChannel.send(f"**{GuildMember.name}** just bought {quantity} shares of {ticker} for ${cost:,.2f}")
        return
    
    # This is a transaction for the Investant Total Money Market Fund
    elif ctx.channel.id != InvestantTotalMoneyMarketFund: # Wrong Channel
        await ctx.send(f"Please process all **Investant Total Money Market Fund** transactions in <#{InvestantTotalMoneyMarketFund}>.", ephemeral = UserSeesOnly)
        return

    else: # Process Investant Total Money Market Fund purchase order

        # Check if the ITMM Fund already has [20] open positions
        DBCursor = PaperTradeDB.cursor() # Open Cursor
        DBCursor.execute("SELECT COUNT(Holding) FROM ServerPortfolios WHERE ServerID = %s AND PortfolioName = %s AND Holding != %s AND Holding != %s", (str(InvestantServerID), "Investant Total Money Market Fund", "Cash Balance", "Cash Proceeds"))
        ITMMHoldingsCount = DBCursor.fetchone()[0]
        if ITMMHoldingsCount >= 20:
            DBCursor.close()
            await ctx.send(f"I'm sorry, <@{UserID}>, the ITMM currently has {ITMMHoldingsCount} open positions and has reached our allowed limit.\nAs Investant grows, we will upgrade database and server size to allow for more complex portfolios with even more open positions.", ephemeral = UserSeesOnly)
            return

        # Grab Fund's Cash Balance
        DBCursor.execute("SELECT TotalCost FROM ServerPortfolios WHERE ServerID = %s AND PortfolioName = %s AND Holding = %s", (str(InvestantServerID), "Investant Total Money Market Fund", "Cash Balance")) # Fetch ITMM Cash Balance
        ITMMCashBalance = DBCursor.fetchone()[0]

        if cost > ITMMCashBalance: # Hedge Fund Manager attempted to purchase more than the fund can afford
            DBCursor.close() # Close Cursor
            await ctx.send(f"Insufficient Funds. I'm sorry, {GuildMember.name}, the **Investant Total Money Market Fund** currently has a cash balance of ${ITMMCashBalance:,.2f}.", ephemeral = UserSeesOnly)
            return

        # Check if ITMM already holds this equity. We only need Quantity and AvgCost for calcs, so grab them if they exist
        DBCursor.execute("SELECT Quantity, AvgCost, TotalCost FROM ServerPortfolios WHERE ServerID = %s AND PortfolioName = %s AND Holding = %s", (str(InvestantServerID), "Investant Total Money Market Fund", ticker))
        Result = DBCursor.fetchall()

        # Purchase will execute, so prepare CashFlowChannel
        CashFlowChannel = await interactions.get(PaperTradeBot, interactions.Channel, object_id = CashFlow)

        if len(Result) > 0: # If ticker is already in the fund, purchase more shares

            # Gather previous data from User's position and prepare new data for deployment
            CurrentQuantity, CurrentAvgCost, CurrentTotalCost = Result[0][0], Result[0][1], Result[0][2]
            NewQuantity = CurrentQuantity + quantity
            NewAvgCost = round(((CurrentAvgCost * CurrentQuantity) + cost) / (NewQuantity), 7)
            NewTotalCost = round(CurrentTotalCost + cost, 2)

            # Insert new data about position after buy transaction
            DBCursor.execute("UPDATE ServerPortfolios SET Quantity = %s, AvgCost = %s, TotalCost = %s WHERE ServerID = %s AND PortfolioName = %s AND Holding = %s", (NewQuantity, NewAvgCost, NewTotalCost, str(InvestantServerID), "Investant Total Money Market Fund", ticker))
            
            # Update Investant Total Money Market Fund's Cash Balance
            NewCashBalance = round(ITMMCashBalance - cost, 2)
            DBCursor.execute("UPDATE ServerPortfolios SET TotalCost = %s WHERE ServerID = %s AND PortfolioName = %s AND Holding = %s", (NewCashBalance, str(InvestantServerID), "Investant Total Money Market Fund", "Cash Balance"))

        else: # If ticker not in ITMM, add it to the fund
            # Insert data about new position
            DBCursor.execute("INSERT INTO ServerPortfolios (ServerID, PortfolioName, Holding, Quantity, AvgCost, TotalCost) VALUES (%s, %s, %s, %s, %s, %s)", (str(InvestantServerID), "Investant Total Money Market Fund", ticker, quantity, price, cost))
            # Update Investant Total Money Market Fund's Cash Balance
            NewCashBalance = round(ITMMCashBalance - cost, 2)
            DBCursor.execute("UPDATE ServerPortfolios SET TotalCost = %s WHERE ServerID = %s AND PortfolioName = %s AND Holding = %s", (NewCashBalance, str(InvestantServerID), "Investant Total Money Market Fund", "Cash Balance"))

        # Commit these changes to the database
        PaperTradeDB.commit()
        DBCursor.close() # Close Cursor

        # Send message to PaperTrade channel and Cash Flow channel
        String = ITMMBuyString(UserID, quantity, ticker, cost, price, NewCashBalance)
        await ctx.send(String)
        await CashFlowChannel.send(String)
        return

# /sell MAIN METHOD
async def SellMainMethod(ctx, PaperTradeBot, PaperTradeDB, UserID, InvestantServerID, InvestantTotalMoneyMarketFund, CashFlow, UserDMChannel, PaperTrade, PaperTradeGold, quantity, ticker, itmm):
    
    if itmm: # THIS IS FOR THE ITMM FUND
        if ctx.channel_id != InvestantTotalMoneyMarketFund:
            await ctx.send(f"Please process all **Investant Total Money Market Fund** transactions in <#{InvestantTotalMoneyMarketFund}>.", ephemeral = True)
            return
        
        else: # MAIN ITMM SELL PROCESS
            # Check if ITMM holds this equity | We only need Quantity and AvgCost for calcs, so grab them if they exist
            ticker = ticker.upper() # Make the ticker uppercase
            DBCursor = PaperTradeDB.cursor() # Open Cursor
            DBCursor.execute("SELECT Quantity, AvgCost, TotalCost FROM ServerPortfolios WHERE ServerID = %s AND PortfolioName = %s AND Holding = %s", (str(InvestantServerID),"Investant Total Money Market Fund", ticker))
            Result = DBCursor.fetchall()

            if len(Result) > 0: # If ticker is already in fund, begin sell process

                CurrentQuantity = Result[0][0]

                if quantity > CurrentQuantity: # If user is attempting to sell more than the fund currently holds, return error
                    DBCursor.close() # Close Cursor
                    await ctx.send(f"Insufficient Share Volume. I'm sorry, <@{UserID}>, the **Investant Total Money Market Fund** currently contains {CurrentQuantity} shares of {ticker}.", ephemeral = True)
                    return
                
                # Sell transaction will execute, so prepare CashFlowChannel and required criteria
                CashFlowChannel = await interactions.get(PaperTradeBot, interactions.Channel, object_id = CashFlow)
                CurrentAvgCost = Result[0][1]
                CurrentTotalCost = Result[0][2]

                # Grab ITMM cash balance and cash proceeds
                DBCursor.execute("SELECT TotalCost FROM ServerPortfolios WHERE ServerID = %s AND PortfolioName = %s AND Holding = %s", (str(InvestantServerID), "Investant Total Money Market Fund", "Cash Balance")) # Fetch Fund's Cash Balance
                ITMMCashBalance = DBCursor.fetchone()[0]
                DBCursor.execute("SELECT TotalCost FROM ServerPortfolios WHERE ServerID = %s AND PortfolioName = %s AND Holding = %s", (str(InvestantServerID), "Investant Total Money Market Fund", "Cash Proceeds")) # Fetch Fund's Cash Proceeds
                ITMMCashProceeds = DBCursor.fetchone()[0]

                # Main Sell Process
                stock = yf.Ticker(ticker)
                price = round(stock.history().tail(1)['Close'][0], 2)
                proceeds = round(price * quantity, 2)
                gainloss = round(proceeds - (CurrentAvgCost * quantity), 2)

                # If the fund has sold its entire position, delete the record of this holding
                if CurrentQuantity == quantity:
                    DBCursor.execute("DELETE FROM ServerPortfolios WHERE ServerID = %s AND PortfolioName = %s AND Holding = %s", (str(InvestantServerID), "Investant Total Money Market Fund", ticker))

                # Partial sell of fund's position, update values
                else:
                    NewQuantity = CurrentQuantity - quantity
                    NewTotalCost = round(CurrentTotalCost - proceeds, 2)
                    DBCursor.execute("UPDATE ServerPortfolios SET Quantity = %s, TotalCost = %s WHERE ServerID = %s AND PortfolioName = %s AND Holding = %s", (NewQuantity, NewTotalCost, str(InvestantServerID), "Investant Total Money Market Fund", ticker))

                # Update the Fund's Cash Balance and Cash Proceeds
                NewCashBalance = round(ITMMCashBalance + proceeds, 2)
                NewCashProceeds = round(ITMMCashProceeds + gainloss, 2)
                DBCursor.execute("UPDATE ServerPortfolios SET TotalCost = %s WHERE ServerID = %s AND PortfolioName = %s AND Holding = %s", (NewCashBalance, str(InvestantServerID), "Investant Total Money Market Fund", "Cash Balance"))
                DBCursor.execute("UPDATE ServerPortfolios SET TotalCost = %s WHERE ServerID = %s AND PortfolioName = %s AND Holding = %s", (NewCashProceeds, str(InvestantServerID), "Investant Total Money Market Fund", "Cash Proceeds"))

                # Commit these changes to the database
                PaperTradeDB.commit()
                DBCursor.close() # Close Cursor

                # Send message to ITMM channel and Cash Flow channel
                String = ITMMSellString(UserID, quantity, ticker, proceeds, price, NewCashBalance)
                await ctx.send(String)
                await CashFlowChannel.send(String)
                return
            
            else: # User attempted to sell an equity that the fund doesn't hold
                DBCursor.close()
                await ctx.send(f"Insufficient Share Volume. We're sorry, <@{UserID}>, but the **Investant Total Money Market Fund** doesn't currently hold {ticker}.", ephemeral = True)
                return

    else: # MAIN PERSONAL HOLDING SELL PROCESS

        # WRONG CHANNEL
        if ctx.channel_id not in [PaperTrade, PaperTradeGold, UserDMChannel.id]:
            await ctx.send(f"This command is restricted to <#{PaperTrade}> and <#{PaperTradeGold}>.", ephemeral =True)
            return

        # Check if user already owns this equity
        ticker = ticker.upper() # Make the ticker uppercase
        DBCursor = PaperTradeDB.cursor() # Open Cursor
        DBCursor.execute("SELECT Quantity, AvgCost, TotalCost FROM PortfolioHoldings WHERE UserID = %s AND Holding = %s", (str(UserID), ticker)) # We only need Quantity and AvgCost for calcs, so grab them if they exist
        Result = DBCursor.fetchall()

        if len(Result) > 0: # If ticker is already in portfolio, begin sell process

            CurrentQuantity = Result[0][0]

            if quantity > CurrentQuantity: # If user is attempting to sell more than they own, return error
                DBCursor.close() # Close Cursor
                await ctx.send(f"Insufficient Share Volume. Your portfolio contains {CurrentQuantity} shares of {ticker}.", ephemeral = True)
                return
            
            # Sell transaction will execute, so prepare CashFlowChannel and required criteria
            CashFlowChannel = await interactions.get(PaperTradeBot, interactions.Channel, object_id = CashFlow)
            CurrentAvgCost = Result[0][1]
            CurrentTotalCost = Result[0][2]

            # Grab User's cash balance and cash proceeds
            DBCursor.execute("SELECT TotalCost FROM PortfolioHoldings WHERE UserID = %s AND Holding = %s", (str(UserID), "Cash Balance")) # Fetch User's Cash Balance
            UserCashBalance = DBCursor.fetchone()[0]
            DBCursor.execute("SELECT TotalCost FROM PortfolioHoldings WHERE UserID = %s AND Holding = %s", (str(UserID), "Cash Proceeds")) # Fetch User's Cash Proceeds
            UserCashProceeds = DBCursor.fetchone()[0]

            # Main Sell Process
            stock = yf.Ticker(ticker)
            price = round(stock.history().tail(1)['Close'][0], 2)
            proceeds = round(price * quantity, 2)
            gainloss = round(proceeds - (CurrentAvgCost * quantity), 2)

            # If the user has sold their entire position, delete the record of this holding from PortfolioHoldings
            if CurrentQuantity == quantity:
                DBCursor.execute("DELETE FROM PortfolioHoldings WHERE UserID = %s AND Holding = %s", (str(UserID), ticker))

            # User is selling only part of their position, update values in PortfolioHoldings
            else:
                NewQuantity = CurrentQuantity - quantity
                NewTotalCost = round(CurrentTotalCost - proceeds, 2)
                DBCursor.execute("UPDATE PortfolioHoldings SET Quantity = %s, TotalCost = %s WHERE UserID = %s AND Holding = %s", (NewQuantity, NewTotalCost, str(UserID), ticker))

            # Update the user's Cash Balance and Cash Proceeds in PortfolioHoldings
            NewCashBalance = round(UserCashBalance + proceeds, 2)
            NewCashProceeds = round(UserCashProceeds + gainloss, 2)
            DBCursor.execute("UPDATE PortfolioHoldings SET TotalCost = %s WHERE UserID = %s AND Holding = %s", (NewCashBalance, str(UserID), "Cash Balance"))
            DBCursor.execute("UPDATE PortfolioHoldings SET TotalCost = %s WHERE UserID = %s AND Holding = %s", (NewCashProceeds, str(UserID), "Cash Proceeds"))

            # Commit these changes to the database
            PaperTradeDB.commit()
            DBCursor.close() # Close Cursor

            # Send message to PaperTrade channel and Cash Flow channel
            await ctx.send(f"<@{UserID}> sold {quantity} shares of {ticker} for ${proceeds:,.2f} at ${price:,.2f} per share")
            await CashFlowChannel.send(f"**{ctx.author.name}** just sold {quantity} shares of {ticker} for ${proceeds:,.2f}")
            return
        
        else: # User attempted to sell an equity that they don't own
            DBCursor.close()
            await ctx.send(f"Insufficient Share Volume. We're sorry, <@{UserID}>, but we don't have it in our records that you own {ticker}.", ephemeral = True)
            return

# /price MAIN METHOD
async def PriceMainMethod(ctx, ticker):
    ticker = ticker.upper() # Make the ticker uppercase
    equity = yf.Ticker(ticker)
    price = round(equity.history().tail(1)['Close'][0], 2)
    await ctx.send(f"The current price of {ticker} is ${price:,.2f}")
    return

# /news MAIN METHOD
async def NewsMainMethod(ctx, GuildMember, ticker, DirectMessage):
    ticker = ticker.upper() # Make the ticker uppercase
    TickerNews = TGetNews(ticker)
    await ctx.user.send(TickerNews)
    if DirectMessage:
        return
    await ctx.send(f"Hey, <@{GuildMember.user.id}>, I sent you some news about **{ticker}**.")
    return

# /revenue MAIN METHOD
async def RevenueMainMethod(ctx, ticker):
    stock = yq.Ticker(ticker.upper())
    Data = stock.income_statement(frequency = 'a')

    Revenue, RevGrowth, Year = [], [], []

    for i in range(len(Data)):

        if Data.iloc[i][1] != '12M': # If this is not annual data, then skip it
            continue

        CurrentRev = Data.iloc[i]['TotalRevenue']
        Revenue.append(CurrentRev)
        Year.append(str(Data.iloc[i][0])[:4]) # Grabs the first 4 digits (the year) from the datetime as a string

        if i == 0: # No information for revenue growth on year 0
            RevGrowth.append(0)
            continue

        PreviousRev = Revenue[i - 1]
        RevChange = round(((CurrentRev / PreviousRev) - 1) * 100, 2)
        RevGrowth.append(RevChange)

    TotalIndices = len(Year)
    LastIndex = TotalIndices - 1

    AverageRevenueGrowth = round(np.sum(RevGrowth) / LastIndex, 2)

    Output = f"Revenue for **{ticker}** in {Year[LastIndex]} was ${Revenue[LastIndex]:,.2f}.\n"
    Output += "-----------------------------------------------------------------------\n"
    Output += f"*This is a {RevGrowth[LastIndex]}% increase from the year prior.*\n"
    Output += f"*{ticker} has averaged {AverageRevenueGrowth}% growth in revenue per year for the last {LastIndex} years.*"
    await ctx.send(Output)

# /bank MAIN METHOD
async def BankMainMethod(ctx, PaperTradeDB, UserID, UserSeesOnly):
    # Grab User's checking balance from BankingAccounts table
    DBCursor = PaperTradeDB.cursor() # Open Cursor
    DBCursor.execute("SELECT Checking, Savings FROM BankingAccounts WHERE UserID = %s", [str(UserID)])
    Result = DBCursor.fetchone()
    DBCursor.close() # Close Cursor
    UserChecking, UserSavings = Result[0], Result[1]

    BankingString = GenerateBankingString(UserID, UserChecking, UserSavings)
    await ctx.send(BankingString, ephemeral = UserSeesOnly)

# /pay MAIN METHOD
async def PayMainMethod(ctx, PaperTradeBot, PaperTradeDB, UserID, RecipientID, amount, CashFlow):
    # Gather user credentials
    PayingUserID = UserID
    Amount = round(amount, 2)

    # Validate that payer has sufficient funds for transaction
    DBCursor = PaperTradeDB.cursor() # Open Cursor
    DBCursor.execute("SELECT Checking FROM BankingAccounts WHERE UserID = %s", [str(PayingUserID)])
    PayingCheckingBalance = DBCursor.fetchone()[0]

    if Amount > PayingCheckingBalance: # User attempted to pay another user more than they have available in their checking
        DBCursor.close() # Close Cursor
        await ctx.send(f"I'm sorry, <@{PayingUserID}>. You have insufficient funds for this transaction. You currently have ${PayingCheckingBalance:,.2f} in your Checking Account.", ephemeral = True)
        return
    
    # Transaction will process | Fetch Recipient Checking Balance
    DBCursor.execute("SELECT Checking FROM BankingAccounts WHERE UserID = %s", [str(RecipientID)])
    ReceivingCheckingBalance = DBCursor.fetchone()[0]

    # Calculate new values and process to database
    NewPayingCheckingBalance = round(PayingCheckingBalance - Amount, 2)
    NewReceivingCheckingBalance = round(ReceivingCheckingBalance + Amount, 2)
    DBCursor.execute("UPDATE BankingAccounts SET Checking = %s WHERE UserID = %s", (NewPayingCheckingBalance, str(PayingUserID)))
    DBCursor.execute("UPDATE BankingAccounts SET Checking = %s WHERE UserID = %s", (NewReceivingCheckingBalance, str(RecipientID)))
    
    # Commit these changes
    PaperTradeDB.commit()
    DBCursor.close() # Close Cursor

    CashFlowChannel = await interactions.get(PaperTradeBot, interactions.Channel, object_id = CashFlow)

    # Relay message to users
    await ctx.send(f"You paid ${Amount:,.2f} to <@{RecipientID}>. Your new Checking Balance is ${NewPayingCheckingBalance:,.2f}.", ephemeral = True)
    await CashFlowChannel.send(f"<@{RecipientID}> received a ${Amount:,.2f} payment from <@{PayingUserID}>")
    return

# /itmm MAIN METHOD
async def itmmMainMethod(ctx, PaperTradeDB, InvestantServerID, Gold: bool):
    # Grab ITMM Cash Balance
    DBCursor = PaperTradeDB.cursor() # Open Cursor
    DBCursor.execute("SELECT TotalCost FROM ServerPortfolios WHERE ServerID = %s AND PortfolioName = %s AND Holding = %s", (str(InvestantServerID), "Investant Total Money Market Fund", "Cash Balance"))
    ITMMCashBalance = DBCursor.fetchone()[0]

    # Grab ITMM total cash proceeds
    DBCursor.execute("SELECT TotalCost FROM ServerPortfolios WHERE ServerID = %s AND PortfolioName = %s AND Holding = %s", (str(InvestantServerID), "Investant Total Money Market Fund", "Cash Proceeds"))
    ITMMCashProceeds = DBCursor.fetchone()[0]

    # Grab ITMM positions other than cash
    DBCursor.execute("SELECT * FROM ServerPortfolios WHERE ServerID = %s AND PortfolioName = %s AND Holding != %s AND Holding != %s", (str(InvestantServerID), "Investant Total Money Market Fund", "Cash Balance", "Cash Proceeds"))
    Positions = DBCursor.fetchall()

    # Grab the number of users invested in the ITMM
    DBCursor.execute("SELECT DISTINCT UserID FROM PortfolioHoldings WHERE Holding = %s", ["Investant Total Money Market Fund"])
    NumUsersInvested = len(DBCursor.fetchall())
    DBCursor.close() # Close Cursor

    # Generate the embed and send to user
    embed, files = GenerateITMMEmbed(Positions, ITMMCashBalance, ITMMCashProceeds, NumUsersInvested, Gold)
    await ctx.send(embeds = embed, files = files)
    return

# /salary MAIN METHOD
async def SalaryMainMethod(ctx, PaperTradeDB, UserID, UserSeesOnly):
    # Grab user's salary
    DBCursor = PaperTradeDB.cursor() # Open Cursor
    DBCursor.execute("SELECT Job, Salary FROM DiscordUserInfo WHERE UserID = %s", [str(UserID)])
    Result = DBCursor.fetchone()
    DBCursor.close()

    UserJob = Result[0]
    UserSalary = Result[1]
    # 0.01916496 derives from 1461 days in a 4-year period with leap years, divided by 28 (7 days/week * 4 years)
    UserPayments = round(UserSalary * 0.01916496, 2) # Weekly Payments

    String = SalaryString(UserID, UserJob, UserSalary, UserPayments)
    await ctx.send(String, ephemeral = UserSeesOnly)
    return

# /transfer MAIN METHOD
async def TransferMainMethod(ctx, withdraw, deposit, amount, UserID, PaperTradeDB, PaperTradeBot, CashFlow, UserSeesOnly):
    # Validate whether user entered duplicate account
    if withdraw == deposit:
        FailedTransferString = GenerateFailedTransferString(UserID)
        await ctx.send(FailedTransferString, ephemeral = True)

    # We will need to query the PaperTradeDB database, so prepare the cursor and Amount
    TransferAmount = round(amount, 2)
    DBCursor = PaperTradeDB.cursor() # Open Cursor

    # region SWITCH STATEMENT
    match withdraw:
        case "portfolio": # Withdrawing from portfolio
            # Validate whether the user has sufficient funds to make the transer
            DBCursor.execute("SELECT TotalCost FROM PortfolioHoldings WHERE UserID = %s AND Holding = %s", (str(UserID), "Cash Balance"))
            CashBalance = round(DBCursor.fetchone()[0], 2)

            if TransferAmount > CashBalance: # User attempted to transfer more than is available in their portfolio cash balance
                DBCursor.close() # Close Cursor
                await ctx.send(f"I'm sorry, <@{UserID}>, but you have insufficient funds available for this transaction. Your portfolio cash balance is currently ${CashBalance:,.2f}.", ephemeral = UserSeesOnly)
                return
            
            match deposit:
                case "checking": # Depositing to checking
                    # Query database for their current checking balance
                    DBCursor.execute("SELECT Checking FROM BankingAccounts WHERE UserID = %s", [str(UserID)])
                    CheckingBalance = round(DBCursor.fetchone()[0])
                    
                    # Calculate new values for Cash Balance and Checking Balance
                    NewCashBalance = round(CashBalance - TransferAmount, 2)
                    NewCheckingBalance = round(CheckingBalance + TransferAmount, 2)

                    # Update Tables with new balances
                    DBCursor.execute("UPDATE PortfolioHoldings SET TotalCost = %s WHERE UserID = %s AND Holding = %s", (NewCashBalance, str(UserID), "Cash Balance"))
                    DBCursor.execute("UPDATE BankingAccounts SET Checking = %s WHERE UserID = %s", (NewCheckingBalance, str(UserID)))
                    PaperTradeDB.commit() # Commit these changes
                    DBCursor.close() # Close Cursor

                    CashFlowChannel = await interactions.get(PaperTradeBot, interactions.Channel, object_id = CashFlow)

                    # Send message transaction processed
                    await ctx.send(f"Hey, <@{UserID}>! We've received your request to transfer ${TransferAmount:,.2f}. Your Portfolio Cash Balance is now ${NewCashBalance:,.2f} and your Checking Balance is now ${NewCheckingBalance:,.2f}.", ephemeral = UserSeesOnly)
                    await CashFlowChannel.send(f"**{ctx.author.name}** just withdrew ${TransferAmount:,.2f} from their portfolio")
                    return
                
                case "savings": # Depositing to savings
                    # Query database for their current savings balance
                    DBCursor.execute("SELECT Savings FROM BankingAccounts WHERE UserID = %s", [str(UserID)])
                    SavingsBalance = round(DBCursor.fetchone()[0], 2)
                    
                    # Calculate new values for Cash Balance and Savings Balance
                    NewCashBalance = round(CashBalance - TransferAmount, 2)
                    NewSavingsBalance = round(SavingsBalance + TransferAmount, 2)

                    # Update Tables with new balances
                    DBCursor.execute("UPDATE PortfolioHoldings SET TotalCost = %s WHERE UserID = %s AND Holding = %s", (NewCashBalance, str(UserID), "Cash Balance"))
                    DBCursor.execute("UPDATE BankingAccounts SET Savings = %s WHERE UserID = %s", (NewSavingsBalance, str(UserID)))
                    PaperTradeDB.commit() # Commit these changes
                    DBCursor.close() # Close Cursor

                    CashFlowChannel = await interactions.get(PaperTradeBot, interactions.Channel, object_id = CashFlow)

                    # Send message transaction processed
                    await ctx.send(f"Hey, <@{UserID}>! We've received your request to transfer ${TransferAmount:,.2f}. Your Portfolio Cash Balance is now ${NewCashBalance:,.2f} and your Savings Balance is now ${NewSavingsBalance:,.2f}.", ephemeral = UserSeesOnly)
                    await CashFlowChannel.send(f"**{ctx.author.name}** just withdrew ${TransferAmount:,.2f} from their portfolio")
                    return
        
        case "checking": # Withdrawing from checking
            # Validate whether the user has sufficient funds to make the transer
            DBCursor.execute("SELECT Checking FROM BankingAccounts WHERE UserID = %s", [str(UserID)])
            CheckingBalance = round(DBCursor.fetchone()[0])

            if TransferAmount > CheckingBalance: # User attempted to transfer more than is available in their checking account balance
                DBCursor.close() # Close Cursor
                await ctx.send(f"I'm sorry, <@{UserID}>, but you have insufficient funds available for this transaction. Your checking account balance is currently ${CheckingBalance:,.2f}.", ephemeral = UserSeesOnly)
                return

            match deposit:
                case "portfolio": # Depositing to portfolio
                    # Query database for their current portfolio cash balance
                    DBCursor.execute("SELECT TotalCost FROM PortfolioHoldings WHERE UserID = %s AND Holding = %s", (str(UserID), "Cash Balance"))
                    CashBalance = round(DBCursor.fetchone()[0], 2)
                    
                    # Calculate new values for Cash Balance and Checking Balance
                    NewCashBalance = round(CashBalance + TransferAmount, 2)
                    NewCheckingBalance = round(CheckingBalance - TransferAmount, 2)

                    # Update Tables with new balances
                    DBCursor.execute("UPDATE PortfolioHoldings SET TotalCost = %s WHERE UserID = %s AND Holding = %s", (NewCashBalance, str(UserID), "Cash Balance"))
                    DBCursor.execute("UPDATE BankingAccounts SET Checking = %s WHERE UserID = %s", (NewCheckingBalance, str(UserID)))
                    PaperTradeDB.commit() # Commit these changes
                    DBCursor.close() # Close Cursor

                    CashFlowChannel = await interactions.get(PaperTradeBot, interactions.Channel, object_id = CashFlow)

                    # Send message transaction processed
                    await ctx.send(f"Hey, <@{UserID}>! We've received your request to transfer ${TransferAmount:,.2f}. Your Portfolio Cash Balance is now ${NewCashBalance:,.2f} and your Checking Balance is now ${NewCheckingBalance:,.2f}.", ephemeral = UserSeesOnly)
                    await CashFlowChannel.send(f"**{ctx.author.name}** just deposited ${TransferAmount:,.2f} to their portfolio")
                    return

                case "savings": # Depositing to savings
                    # Query database for their current savings balance
                    DBCursor.execute("SELECT Savings FROM BankingAccounts WHERE UserID = %s", [str(UserID)])
                    SavingsBalance = round(DBCursor.fetchone()[0], 2)
                    
                    # Calculate new values for Cash Balance and Savings Balance
                    NewCheckingBalance = round(CheckingBalance - TransferAmount, 2)
                    NewSavingsBalance = round(SavingsBalance + TransferAmount, 2)

                    # Update Tables with new balances
                    DBCursor.execute("UPDATE BankingAccounts SET Checking = %s WHERE UserID = %s", (NewCheckingBalance, str(UserID)))
                    DBCursor.execute("UPDATE BankingAccounts SET Savings = %s WHERE UserID = %s", (NewSavingsBalance, str(UserID)))
                    PaperTradeDB.commit() # Commit these changes
                    DBCursor.close() # Close Cursor

                    # Send message transaction processed
                    await ctx.send(f"Hey, <@{UserID}>! We've received your request to transfer ${TransferAmount:,.2f}. Your Checking Account Balance is now ${NewCheckingBalance:,.2f} and your Savings Balance is now ${NewSavingsBalance:,.2f}.", ephemeral = UserSeesOnly)
                    return
        
        case "savings": # Withdraw from savings
            # Validate whether the user has sufficient funds to make the transer
            DBCursor.execute("SELECT Savings FROM BankingAccounts WHERE UserID = %s", [str(UserID)])
            SavingsBalance = round(DBCursor.fetchone()[0], 2)

            if TransferAmount > SavingsBalance: # User attempted to transfer more than is available in their savings account balance
                DBCursor.close() # Close Cursor
                await ctx.send(f"I'm sorry, <@{UserID}>, but you have insufficient funds available for this transaction. Your savings account balance is currently ${SavingsBalance:,.2f}.", ephemeral = UserSeesOnly)
                return
            
            match deposit:
                case "portfolio": # Depositing to portfolio
                    # Query database for their current portfolio cash balance
                    DBCursor.execute("SELECT TotalCost FROM PortfolioHoldings WHERE UserID = %s AND Holding = %s", (str(UserID), "Cash Balance"))
                    CashBalance = round(DBCursor.fetchone()[0], 2)
                    
                    # Calculate new values for Cash Balance and Savings Balance
                    NewCashBalance = round(CashBalance + TransferAmount, 2)
                    NewSavingsBalance = round(SavingsBalance - TransferAmount, 2)

                    # Update Tables with new balances
                    DBCursor.execute("UPDATE PortfolioHoldings SET TotalCost = %s WHERE UserID = %s AND Holding = %s", (NewCashBalance, str(UserID), "Cash Balance"))
                    DBCursor.execute("UPDATE BankingAccounts SET Savings = %s WHERE UserID = %s", (NewSavingsBalance, str(UserID)))
                    PaperTradeDB.commit() # Commit these changes
                    DBCursor.close() # Close Cursor

                    CashFlowChannel = await interactions.get(PaperTradeBot, interactions.Channel, object_id = CashFlow)

                    # Send message transaction processed
                    await ctx.send(f"Hey, <@{UserID}>! We've received your request to transfer ${TransferAmount:,.2f}. Your Portfolio Cash Balance is now ${NewCashBalance:,.2f} and your Savings Balance is now ${NewSavingsBalance:,.2f}.", ephemeral = UserSeesOnly)
                    await CashFlowChannel.send(f"**{ctx.author.name}** just deposited ${TransferAmount:,.2f} to their portfolio")
                    return

                case "checking": # Depositing to checking
                    # Query database for their current checking balance
                    DBCursor.execute("SELECT Checking FROM BankingAccounts WHERE UserID = %s", [str(UserID)])
                    CheckingBalance = round(DBCursor.fetchone()[0], 2)

                    # Calculate new values for Savings Balance and Checking Balance
                    NewSavingsBalance = round(SavingsBalance - TransferAmount, 2)
                    NewCheckingBalance = round(CheckingBalance + TransferAmount, 2)

                    # Update Tables with new balances
                    DBCursor.execute("UPDATE BankingAccounts SET Savings = %s WHERE UserID = %s", (NewSavingsBalance, str(UserID)))
                    DBCursor.execute("UPDATE BankingAccounts SET Checking = %s WHERE UserID = %s", (NewCheckingBalance, str(UserID)))
                    PaperTradeDB.commit() # Commit these changes
                    DBCursor.close() # Close Cursor

                    # Send message transaction processed
                    await ctx.send(f"Hey, <@{UserID}>! We've received your request to transfer ${TransferAmount:,.2f}. Your Savings Balance is now ${NewSavingsBalance:,.2f} and your Checking Balance is now ${NewCheckingBalance:,.2f}.", ephemeral = UserSeesOnly)
                    return
    # endregion

# endregion MAIN METHODS
# ------------------------------------------------------------------------------------------------------------------------------------------------------------