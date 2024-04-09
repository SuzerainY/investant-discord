# PaperTrade Features


Planned features for multiple assets of the platform and subcategories. Some features currently being added, modified, or planned for future addition.

When features are successfully added, a community post should be sent informing users.


# Discord Features:


### Only Available in [Investant Discord](https://discord.gg/SFUKKjWEjH)
* Checking and Savings Accounts and commands
    * All users will have a checking account where they receive weekly paychecks based on their salaries. They can make deposits and/or withdrawals from their portfolios via their checking account.
    * There will be items and promotionals that can be purchased with their checking balances | ***To be added***
    * Savings accounts earn a high yield we adjust periodically with market
    * /bank command to view bank accounts
    * /transfer &lt;checking/savings> &lt;checking savings> transfer from left to right


### PaperTrade Dependencies


pip install...
* discord-py-interactions | version 4.4.0
* yfinance
* yahooquery
* numpy
* pandas
* mysql-connector-python | version 8.0.32
* interactions-tasks | version 1.0.0
* interactions-files | version 1.1.5


## Paper Trade (Standard):


* New Users assigned a random job with a salary range and cash deposit upon entry
* Place market buy & sell orders (transaction sent to _💵cash-flow_ channel)
    * Trading Hours from 9:30am to 4:00pm ET | ***To be added***
* Check the current market price of any equity
* Receive recent news about any equity
* Receive annual revenue and revenue growth information about any company
    * Send as decorative embedded message w/branding
* Trade CryptoCurrencies
    * Handle “-USD” suffix on all cryptocurrencies *To be added*
* DM user their complete portfolio (sent as decorative embedded message w/branding)
    * Net Value w/current prices of equities
        * Calculated as $Cash + \displaystyle\sum_{i=1}^i Q_i \times P_i$
            * Where $Cash$ is the total cash in the portfolio
            * $Q_i$ is the quantity held of the equity
            * $P_i$ is the current price of the equity
    * Total P/L
        * Calculated as $CashProceeds + \displaystyle\sum_{i=1}^i Q_i(P_i - u_i)$
            * Where $CashProceeds$ are realized gains accumulated
            * $u_i$ is the average cost of the equity
    * Percentage P/L
        * Calculated as $( CashProceeds + \displaystyle\sum_{i=1}^i Q_i(P_i - u_i) ) \div CostBasis$
            * Where $CostBasis$ is Total Deposits to Account by user
    * Cash Account Total
    * Every Equity Held
        * \# Shares = $Q$
        * Current Value of Position = $Q \times P$
        * Average Cost/Share = $u$ (calculate to 7 decimal places, display 3)
            * If Equity not in portfolio at time of purchase:
                * $u = (P \times Q) \div Q$
            * Else:
                * $u = (( u_t-1 \times Q_t-1 ) + ( P_t \times Q_t )) \div Q$

                * Where $u_t-1$ is the previous Average Cost/Share
                * $Q_t-1$ is the previous quantity of shares before time t
                * $P_t$ is the current price of the equity at time t
                * $Q_t$ is the quantity of shares being purchased at time t
                * $Q$ is the new total quantity of shares after purchase
        * Current Price = $P$


## Paper Trade Gold:


* Investant Total Money Market Fund
    * Trades can only be placed by Gold members in the _#💱itmm_ channel
    * Full features functionality as individual portfolios
        * Net Value w/current prices of equities
        * Total P/L
        * Percentage P/L
        * Cash Account Total
        * Every Equity Held
            * \# Shares
            * Current Value of Position
            * Average Cost/Share
            * Current Price
* Receive dividend payments to the cash account | ***To be added***
    * Possible ways to iterate through users and payout dividends? Required:
        * Knowledge of every company with an ex-dividend date today, the payment date, and payment amount per share: [Dividend Calendar](https://www.nasdaq.com/market-activity/dividends)
        * Knowledge of every user with the equity who also held the equity BEFORE the ex-dividend date and how many shares they held at crossover (can have script run before market open each day)
        * Have a database table of DividendsDue that is updated every morning:
            * All ex-dividend dates == today
                * For each company, select all users who own it and add record for each user:
                    * User
                    * Payment Date
                    * Dividend Amount
            * Select all payments due today and iterate through
                * Send payment to user’s cash account in portfolio
                * Delete record from table
* After-Hours and Pre-Market Trading | ***To be added***
    * Require after-hours and pre-market pricing information not currently available to our platform
    * Trades from 4am to 8pm ET Monday-Friday
    * Pay for after-hours and pre-market data from more powerful api
