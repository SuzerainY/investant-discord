# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# region IMPORTS

from PaperTradeCommands import *
import yfinance as yf
import interactions
import interactions.ext.files

# endregion IMPORTS
# ------------------------------------------------------------------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# region STRINGS AND EMBEDS GENERATED

# /help generate embed
def HelpEmbed(Gold: bool):
    ImageFile1 = interactions.File(filename = "Images/OriginalLogoInvestantTHIN.png")
    ImageFile2 = interactions.File(filename = "Images/FaviconOriginal.png")
    ImageFile3 = interactions.File(filename = "Images/FaviconTransparent.png")

    if Gold:
        embed = interactions.Embed(title = "**Investant | A Paper Money Platform**", description = "We're Building The Most Advanced Market-Based Paper Economy On Discord", color = 0xEBA773)
        ImageFile4 = interactions.File(filename = "Images/FaviconGOLD.png")
        files = [ImageFile1, ImageFile2, ImageFile3, ImageFile4]
        embed.set_author(name = "PaperTrade", url = "https://discord.gg/SFUKKjWEjH", icon_url = "attachment://FaviconGOLD.png")
    else:
        embed = interactions.Embed(title = "**Investant | A Paper Money Platform**", description = "We're Building The Most Advanced Market-Based Paper Economy On Discord", color = 0x40C9FF)
        ImageFile4 = interactions.File(filename = "Images/FaviconWHITE.png")
        files = [ImageFile1, ImageFile2, ImageFile3, ImageFile4]
        embed.set_author(name = "PaperTrade", url = "https://discord.gg/SFUKKjWEjH", icon_url = "attachment://FaviconWHITE.png")

    embed.set_thumbnail(url = "attachment://FaviconTransparent.png", width = 50, height = 50)
    embed.set_image(url = "attachment://OriginalLogoInvestantTHIN.png")
    embed.set_footer(text = "Investant | A Paper Money Platform", icon_url = "attachment://FaviconOriginal.png")

    embed.add_field(name = "**/portfolio**", value = "Your Current Portfolio", inline = True)
    embed.add_field(name = "**/buy**", value = "Buy an Equity [itmm]", inline = True)
    embed.add_field(name = "**/sell**", value = "Sell an Equity [itmm]", inline = True)

    embed.add_field(name = "**/price**", value = "Current Market Price of Stock", inline = True)
    embed.add_field(name = "**/news**", value = "DMs News About a Stock", inline = True)
    embed.add_field(name = "**/revenue**", value = "Revenue Info About a Stock", inline = True)

    embed.add_field(name = "**/bank**", value = "Your Bank Info", inline = True)
    embed.add_field(name = "**/transfer**", value = "Transfer Funds", inline = True)
    embed.add_field(name = "**/pay**", value = "Pay a Friend", inline = True)

    embed.add_field(name = "**/itmm**", value = "Investant Total Money Market Fund", inline = True)
    embed.add_field(name = "**/salary**", value = "Your Current Salary and Weekly Pay", inline = True)
    return embed, files

# Create message for new members joining the discord server
def NewMemberPrompt(member, Job, Salary, SignOnBonus, PaperTrade):
    prompt = f"**Hello, <@{member.id}>. Welcome to the Investant Community! We know it's your first day on the job, so let's go over things real quick...**\n\n"
    prompt += f"Congratulations on starting your new job as a **{Job}**! Your starting salary is **${Salary:,.2f}** and we have taken the liberty of providing you a sign-on bonus of **${SignOnBonus:,.2f}**.\n"
    prompt += f"The sign-on bonus has been wired to your brokerage account you provided us with. Access it with the **/portfolio** command in <#{PaperTrade}>.\n"
    prompt += "You also have a checking and savings account with the bank. Access them with **/bank** or make transfers with **/transfer**.\n"
    prompt += "Happy trading!"
    return prompt

# Create message for a returning member to the discord server
def ReturningUserMessage(member, Job, UserCashTotal, UserChecking, UserSavings, PaperTrade):
    message = f"Long time no see, <@{member.id}>! Feel free to pick up where you left off as a {Job}...\n"
    message += f"You currently have ${UserCashTotal:,.2f} in your brokerage account that we've been keeping safe for you! Access it with the **/portfolio** command in <#{PaperTrade}>.\n"
    message += f"I also see that you have ${UserChecking:,.2f} in you checking account and ${UserSavings:,.2f} in your savings account. Access them with **/bank** or make transfers with **/transfer**."
    message += "Happy trading!"
    return message

# Create ITMM Embedded Message for /itmm
def GenerateITMMEmbed(Positions, ITMMCashBalance, ITMMCashProceeds, NumUsersInvested, Gold: bool):
    # PREPARE EMBED FOR ADDING ITMM FUND INFORMATION
    ImageFile1 = interactions.File(filename = "Images/OriginalLogoInvestantTHIN.png")
    ImageFile2 = interactions.File(filename = "Images/FaviconOriginal.png")
    ImageFile3 = interactions.File(filename = "Images/FaviconTransparent.png")
    if Gold:
        embed = interactions.Embed(
            title = "Investant | Total Money Market Fund",
            description = "The Investant Total Money Market Fund is a Hedge Fund Internally Managed by InvestantMax Users. Ability to Invest in the Fund Coming Soon.",
            color = 0xEBA773
        )
        ImageFile4 = interactions.File(filename = "Images/FaviconGOLD.png")
        files = [ImageFile1, ImageFile2, ImageFile3, ImageFile4]
        embed.set_author(name = "PaperTrade", url = "https://discord.gg/SFUKKjWEjH", icon_url = "attachment://FaviconGOLD.png")
    else:
        embed = interactions.Embed(
            title = "Investant | Total Money Market Fund",
            description = "The Investant Total Money Market Fund is a Hedge Fund Internally Managed by InvestantMax Users. Ability to Invest in the Fund Coming Soon.",
            color = 0x40C9FF
        )
        ImageFile4 = interactions.File(filename = "Images/FaviconWHITE.png")
        files = [ImageFile1, ImageFile2, ImageFile3, ImageFile4]
        embed.set_author(name = "PaperTrade", url = "https://discord.gg/SFUKKjWEjH", icon_url = "attachment://FaviconWHITE.png")
    embed.set_thumbnail(url = "attachment://FaviconTransparent.png", width = 50, height = 50)
    embed.set_image(url = "attachment://OriginalLogoInvestantTHIN.png")
    embed.set_footer(text = f"Investant | {NumUsersInvested} Users Invested in the ITMM", icon_url = "attachment://FaviconOriginal.png")

    FieldsToEmbed = [] # Prepare list for additional fields to embed

    # Fetch Data from Yahoo Finance API
    symbols = [position[3] for position in Positions]
    data = yf.download(symbols, period='1d', interval="1d", group_by='ticker', progress=False)

    # Calculate Outstanding Investments of Fund
    ITMMTotalMarketValue = 0
    ITMMUnrealizedGain = 0
    for position in Positions:
        symbol = position[3]
        quantity = position[4]
        AvgCost = position[5]
        TotalCost = position[6]
        price = data[symbol].iloc[-1]['Close']
        ITMMTotalMarketValue += (quantity * price)
        ITMMUnrealizedGain += ((price - AvgCost) * quantity)

        PositionEmbedField = {
            "name": f"{symbol}",
            "value": f"P/L: {(((price * quantity) - TotalCost) / TotalCost) * 100:,.2f}%\n# Shares: {quantity}\nCurrent Value: ${price * quantity:,.2f}\nCurrent Price: ${price:,.2f}\nAvg Cost: ${AvgCost:,.2f}"
        }
        FieldsToEmbed.append(PositionEmbedField)

    # ADD ITMM FUND INFORMATION
    embed.add_field(
        name = f"TOTAL VALUE: ${ITMMCashBalance + ITMMTotalMarketValue:,.2f} | Return: {(ITMMUnrealizedGain / ITMMTotalMarketValue) * 100:,.2f}%",
        value = f"Cash: ${ITMMCashBalance:,.2f}\nInvestments: ${ITMMTotalMarketValue:,.2f}\nTotal Proceeds: ${ITMMCashProceeds:,.2f}"
    )
    # ADD INDIVIDUAL POSITION(S) INFORMATION
    for Field in FieldsToEmbed:
        embed.add_field(
            name = Field["name"],
            value = Field["value"]
        )
    # RETURN EMBED AND FILES
    return embed, files

# Create Portfolio Embedded Message for /portfolio
def GeneratePortfolioEmbed(Positions, UserCashBalance, UserCashProceeds, UserChecking, UserSavings, Gold: bool):
    # PREPARE EMBED FOR ADDING ITMM FUND INFORMATION
    ImageFile1 = interactions.File(filename = "Images/OriginalLogoInvestantTHIN.png")
    ImageFile2 = interactions.File(filename = "Images/FaviconOriginal.png")
    ImageFile3 = interactions.File(filename = "Images/FaviconTransparent.png")
    if Gold:
        embed = interactions.Embed(
            title = "Investant | Individual Brokerage Account",
            description = "A Current View of all Balances Tied to your Investant Portfolio",
            color = 0xEBA773
        )
        ImageFile4 = interactions.File(filename = "Images/FaviconGOLD.png")
        files = [ImageFile1, ImageFile2, ImageFile3, ImageFile4]
        embed.set_author(name = "PaperTrade", url = "https://discord.gg/SFUKKjWEjH", icon_url = "attachment://FaviconGOLD.png")
    else:
        embed = interactions.Embed(
            title = "Investant | Individual Brokerage Account",
            description = "A Current View of all Balances Tied to your Investant Portfolio",
            color = 0x40C9FF
        )
        ImageFile4 = interactions.File(filename = "Images/FaviconWHITE.png")
        files = [ImageFile1, ImageFile2, ImageFile3, ImageFile4]
        embed.set_author(name = "PaperTrade", url = "https://discord.gg/SFUKKjWEjH", icon_url = "attachment://FaviconWHITE.png")
    embed.set_thumbnail(url = "attachment://FaviconTransparent.png", width = 50, height = 50)
    embed.set_image(url = "attachment://OriginalLogoInvestantTHIN.png")
    embed.set_footer(text = f"Investant | A Paper Money Platform", icon_url = "attachment://FaviconOriginal.png")

    FieldsToEmbed = [] # Prepare list for additional fields to embed

    # Fetch Data from Yahoo Finance API
    symbols = [position[2] for position in Positions]
    data = yf.download(symbols, period='1d', interval="1d", group_by='ticker', progress=False)

    # Calculate Outstanding Investments
    TotalMarketValue = 0
    UnrealizedGain = 0
    for position in Positions:
        symbol = position[2]
        quantity = position[3]
        AvgCost = position[4]
        TotalCost = position[5]
        price = data[symbol].iloc[-1]['Close']
        TotalMarketValue += (quantity * price)
        UnrealizedGain += ((price - AvgCost) * quantity)

        PositionEmbedField = {
            "name": f"{symbol}",
            "value": f"P/L: {(((price * quantity) - TotalCost) / TotalCost) * 100:,.2f}%\n# Shares: {quantity}\nCurrent Value: ${price * quantity:,.2f}\nCurrent Price: ${price:,.2f}\nAvg Cost: ${AvgCost:,.2f}"
        }
        FieldsToEmbed.append(PositionEmbedField)

    # ADD MARKET INFORMATION
    embed.add_field(
        name = f"TOTAL VALUE: ${UserCashBalance + TotalMarketValue:,.2f} | Return: {(UnrealizedGain / TotalMarketValue) * 100:,.2f}%",
        value = f"Cash: ${UserCashBalance:,.2f}\nInvestments: ${TotalMarketValue:,.2f}\nTotal Proceeds: ${UserCashProceeds:,.2f}"
    )
    # ADD INDIVIDUAL POSITION(S) INFORMATION
    for Field in FieldsToEmbed:
        embed.add_field(
            name = Field["name"],
            value = Field["value"]
        )
    # ADD BANKING INFORMATION
    embed.add_field(
        name = "Bank Accounts",
        value = f"Checking: ${UserChecking:,.2f}\nSavings: ${UserSavings:,.2f}"
    )
    # TOTAL NET WORTH
    embed.add_field(
        name = f"TOTAL NET WORTH: ${UserCashBalance + TotalMarketValue + UserChecking + UserSavings:,.2f}",
        value = ""
    )
    # RETURN EMBED AND FILES
    return embed, files

# Create Salary Payout Embedded Message for weekly salary payouts
def GenerateSalaryPayoutEmbed(NumEmployees, TotalPayout):
    # PREPARE EMBED FOR ADDING SALARY PAYOUT INFORMATION
    ImageFile1 = interactions.File(filename = "Images/OriginalLogoInvestantTHIN.png")
    ImageFile2 = interactions.File(filename = "Images/FaviconOriginal.png")
    ImageFile3 = interactions.File(filename = "Images/FaviconTransparent.png")
    ImageFile4 = interactions.File(filename = "Images/FaviconWHITE.png")
    files = [ImageFile1, ImageFile2, ImageFile3, ImageFile4]
    embed = interactions.Embed(
        title = "Investant | PAYDAY ANNOUNCEMENT",
        description = "Salaries Have Been Processed | Check Your New Account Balances With /bank Or /portfolio",
        color = 0x40C9FF
    )

    # SETUP BASE STRUCTURE OF EMBED
    embed.set_author(name = "PaperTrade", url = "https://discord.gg/SFUKKjWEjH", icon_url = "attachment://FaviconWHITE.png")
    embed.set_thumbnail(url = "attachment://FaviconTransparent.png", width = 50, height = 50)
    embed.set_image(url = "attachment://OriginalLogoInvestantTHIN.png")
    embed.set_footer(text = f"Investant | A Paper Money Platform", icon_url = "attachment://FaviconOriginal.png")

    # RELAY WEEKLY PAYOUT INFO
    embed.add_field(
    name = f"TOTAL PAYOUT: ${TotalPayout:,.2f}",
    value = f"TOTAL EMPLOYEES PAID: {NumEmployees}"
    )
    # RETURN EMBED AND FILES
    return embed, files

# Create BankingString for /bank
def GenerateBankingString(UserID, UserChecking, UserSavings):
    BankingString = f"**Hi <@{UserID}>, please see your current banking information below:**\n\n"
    BankingString += f"Checking Balance: ${UserChecking:,.2f}\n"
    BankingString += f"Savings Balance: ${UserSavings:,.2f}"
    return BankingString

# Create FailedTransferString for /transfer
def GenerateFailedTransferString(UserID):
    FailedTransferString = f"I'm sorry, <@{UserID}>. Please double-check your transfer parameters.\n"
    FailedTransferString += "The Withdraw and Deposit accounts cannot be the same account.\n"
    FailedTransferString += "'Account1' is the balance from which you would like to remove the funds.\n"
    FailedTransferString += "'Account2' is the balance to which you would like to add the funds."
    return FailedTransferString

# ITMM BUY TRANSACTION STRING
def ITMMBuyString(UserID, quantity, ticker, cost, price, NewCashBalance):
    String = "**Investant Total Money Market Fund**\n"
    String += f"<@{UserID}> has processed a **buy** order for {quantity} shares of {ticker} for ${cost:,.2f} at ${price:,.2f} per share.\n"
    String += f"The fund retains a current cash balance of ${NewCashBalance:,.2f}."
    return String

# ITMM SELL TRANSACTION STRING
def ITMMSellString(UserID, quantity, ticker, proceeds, price, NewCashBalance):
    String = "**Investant Total Money Market Fund**\n"
    String += f"<@{UserID}> has processed a **sell** order for {quantity} shares of {ticker} for ${proceeds:,.2f} at ${price:,.2f} per share.\n"
    String += f"The fund now holds a cash balance of ${NewCashBalance:,.2f}."
    return String

# Generate /salary string
def SalaryString(UserID, UserJob, UserSalary, UserPayments):
    String = f"Hey, <@{UserID}>. Your current annual salary as a **{UserJob}** is **${UserSalary:,.2f}**.\n"
    String += f"You will receive weekly payments of **${UserPayments:,.2f}** each Friday."
    return String

# endregion STRINGS AND EMBEDS
# ------------------------------------------------------------------------------------------------------------------------------------------------------------