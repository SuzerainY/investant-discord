# import mysql.connector

# # Credentials for PaperTradeDB database with phpMyAdmin
# # Server Choice "DB-BUF-03 (78.108.x)"
# Host = "78.108.218.47"
# User = "u87111_DE3LxQBqvp"
# Password = "z^TzY.l.Km7TJ@Q3zDDH+for"
# Database = "s87111_PaperTradeDB"

# # InvestantServerID = 1075460690065752216

# PaperTradeDB = mysql.connector.connect(
#     host = Host,
#     user = User,
#     passwd = Password,
#     db = Database,
# )

# DBCursor = PaperTradeDB.cursor()

# # Commit changes to database
# PaperTradeDB.commit()
# DBCursor.close()

# # ------------------------------------------------------------------------------------------------------------------------------------------------------------
# # Table: PortfolioHoldings
# # Fields:
# # ID [int(11)] AUTO_INCREMENT
# # UserID [varchar(100)]
# # Holding [varchar(50)]
# # Quantity [int(12)]
# # AvgCost [double] ALWAYS ROUND TO 7 DECIMAL PLACES TO AVOID FLOATING POINT ERRORS
# # TotalCost [double] ALWAYS ROUND TO 2 DECIMAL PLACES TO AVOID FLOATING POINT ERRORS
# # ------------------------------------------------------------------------------------------------------------------------------------------------------------
# # Table: ServerPortfolios
# # Fields:
# # ID [int(11)] AUTO_INCREMENT
# # ServerID [varchar(100)]
# # PortfolioName [varchar(200)]
# # Holding [varchar(50)]
# # Quantity [int(14)]
# # AvgCost [double] ALWAYS ROUND TO 7 DECIMAL PLACES TO AVOID FLOATING POINT ERRORS
# # TotalCost [double] ALWAYS ROUND TO 2 DECIMAL PLACES TO AVOID FLOATING POINT ERRORS
# # ------------------------------------------------------------------------------------------------------------------------------------------------------------
# # Table: DiscordUserInfo
# # Fields:
# # ID [int(11)] AUTO_INCREMENT
# # UserID [varchar(100)]
# # Job [varchar(40)]
# # Salary [int(10)]
# # ------------------------------------------------------------------------------------------------------------------------------------------------------------
# # Table: BankingAccounts
# # Fields:
# # ID [int(11)] AUTO_INCREMENT
# # UserID [varchar(100)]
# # Checking [double] ALWAYS ROUND TO 2 DECIMAL PLACES TO AVOID FLOATING POINT ERRORS
# # Savings [double] ALWAYS ROUND TO 2 DECIMAL PLACES TO AVOID FLOATING POINT ERRORS
# # ------------------------------------------------------------------------------------------------------------------------------------------------------------