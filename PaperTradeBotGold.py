# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# region IMPORTS

from PaperTradeCommands import *
from PaperTradeTasks import *
from PaperTradeClasses import *
import mysql.connector
import contextlib
import interactions
import interactions.ext.files
import time
import os

dbhost = os.environ.get('PTDBHOST')
dbuser = os.environ.get('PTDBUSER')
dbpasswd = os.environ.get('PTDBPASSWD')
db = os.environ.get('PTDB')
InvestantServerID = os.environ.get('PTINVESTANTSERVERID')
GoldBotToken = os.environ.get('PTGOLDBOTTOKEN')

# endregion IMPORTS
# ------------------------------------------------------------------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# region DATABASE LOGIN AND CREDENTIALS
@contextlib.contextmanager # Create secure connection that will ensure its own disconnection to keep resources clean
def ConnectToPaperTradeDB(dbhost: str, dbuser: str, dbpasswd: str, db: str):
    # Create Database Connection
    DBConnection = mysql.connector.connect(
        host = dbhost,
        user = dbuser,
        passwd = dbpasswd,
        db = db
    )
    try:
        yield DBConnection # Yields Database Connection
    except mysql.connector.Error as TheError:
        print(f"Could not create connection to PaperTradeDB Database: {TheError}")
    finally:
        DBConnection.close() # Close Database Connection

# Keep track of all members currently in guild
KeepingMembers = TrackingMembers()

# Bot IDs
PaperTradeBotID = 1075539986453119086
PaperTradeGoldBotID = 1076566586158239796

# Channel IDs
JobAssignment = 1077003046724309134
CashFlow = 1076568911216115712
PaperTrade = 1075555630296870932
InvestantTotalMoneyMarketFund = 1075589065606451250

# Role IDs
InvestantPlus = 1075629267842514964
InvestantPro = 1075617181175402557
InvestantMax = 1075603607354867732
InvestantGroup = 1075463305637920930
Developer = 1075547410027257956

# Create the bot
PaperTradeBot = interactions.Client(
    token = GoldBotToken,
    scope = InvestantServerID,
    intents = interactions.Intents.DEFAULT | interactions.Intents.GUILD_MESSAGE_CONTENT | interactions.Intents.GUILD_MEMBERS
)

# endregion Login and Startup
# ------------------------------------------------------------------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# region EVENT COMMANDS | DEFINE ALL EVENTS TO OCCUR ON TRIGGER

# region STARTUP PROCESS
@PaperTradeBot.event
async def on_start():
    time.sleep(2)
    print("PaperTradeGOLD is now online.")

    # Fetch All Members
    InvestantGuild = await interactions.get(PaperTradeBot, interactions.Guild, object_id = InvestantServerID)
    AllMembers = await InvestantGuild.get_all_members()
    KeepingMembers.InitiateAllMembers(AllMembers)
    print("All Current Members Being Tracked")
    return
# endregion STARTUP

# region New Member Joined
@PaperTradeBot.event
async def on_guild_member_add(member: interactions.GuildMember):
    print("New Member Joined | Keeping Track For Validation | Not Logging Database")
    KeepingMembers.AddMember(member)
    print(f"New Member [{member.id}] Validated")
    return
# endregion New Member

# endregion EVENT COMMANDS
# ------------------------------------------------------------------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# region /SLASH COMMANDS | DEFINE ALL /SLASH COMMANDS TO BE USED IN THE INVESTANT SERVER

# region /help command
@PaperTradeBot.command(
    name = "help",
    description = f"Sends a list of all possible user commands with PaperTradeGold",
)
async def help(ctx: interactions.CommandContext):
    UserID = ctx.user.id

    if not await IsMemberInGuild(ctx, UserID, KeepingMembers):
        return

    GuildMember = KeepingMembers.GetMember(UserID)
    UserRoles = GuildMember.roles
    UserDMChannel = await GuildMember.user.get_dm_channel()
    # Check if thi is a DM
    UserSeesOnly = True
    if ctx.channel_id == UserDMChannel.id:
        UserSeesOnly = False

    if any(role in UserRoles for role in (InvestantMax, Developer)):
        try:
            embed, files = HelpEmbed(Gold = True) # MAIN
            await ctx.send(embeds = embed, files = files)
        except:
            await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
        return

    # USER IS NOT DEVELOPER OR INVESTANTMAX
    await ctx.send(f"*I'm sorry, do I know you? Maybe you're friends with <@{PaperTradeBotID}>*", ephemeral = UserSeesOnly)
    return
# endregion

# region /portfolio command
# Handle the /portfolio command
@PaperTradeBot.command(
    name = "portfolio",
    description = "Sends your current portfolio",
)
async def portfolio(ctx: interactions.CommandContext):
    UserID = ctx.user.id

    if not await IsMemberInGuild(ctx, UserID, KeepingMembers):
        return

    GuildMember = KeepingMembers.GetMember(UserID)
    UserRoles = GuildMember.roles
    UserDMChannel = await GuildMember.user.get_dm_channel()

    if any(role in UserRoles for role in (InvestantMax, Developer)):
        # Check if this is DM
        if ctx.channel_id == UserDMChannel.id:
            UserSeesOnly = False
            # MAIN PORTFOLIO METHOD
            with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
                await ctx.defer(ephemeral = UserSeesOnly)
                try:
                    await MainPortfolioMethod(ctx, PaperTradeDB, UserID, UserSeesOnly, Gold = True)
                except:
                    await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = UserSeesOnly)
                return

        elif ctx.channel_id != PaperTrade: # Wrong Channel
            await ctx.send(f"This command is restricted to <#{PaperTrade}>.", ephemeral =True)
            return
        
        # MAIN PORTFOLIO METHOD
        UserSeesOnly = True
        with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
            await ctx.defer(ephemeral = UserSeesOnly)
            try:
                await MainPortfolioMethod(ctx, PaperTradeDB, UserID, UserSeesOnly, Gold = True)
            except:
                await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = UserSeesOnly)
            return

    # USER IS NOT DEVELOPER OR INVESTANT MAX
    UserSeesOnly = True
    if ctx.channel_id == UserDMChannel.id:
        UserSeesOnly = False
    await ctx.send(f"*I'm sorry, do I know you? Maybe you're friends with <@{PaperTradeBotID}>*", ephemeral = UserSeesOnly)
    return
# endregion

# region /buy command
@PaperTradeBot.command(
    name = "buy",
    description = "Purchase an equity",
    options = [
        interactions.Option(
            name = "ticker",
            description = "the ticker symbol for the equity you would like to purchase",
            type = interactions.OptionType.STRING,
            required = True
        ),
        interactions.Option(
            name = "quantity",
            description = "the quantity you would like to purchase",
            type = interactions.OptionType.INTEGER,
            required = True,
            min_value = 1
        ),
        interactions.Option(
            name = "itmm",
            description = "optional: is this for the Investant Total Money Market Fund?",
            type = interactions.OptionType.BOOLEAN,
            required = False
        )
    ]
)
async def buy(ctx: interactions.CommandContext, ticker: str, quantity: int, itmm: bool = False):
    UserID = ctx.user.id

    if not await IsMemberInGuild(ctx, UserID, KeepingMembers):
        return

    GuildMember = KeepingMembers.GetMember(UserID)
    UserRoles = GuildMember.roles
    UserDMChannel = await GuildMember.user.get_dm_channel()

    if any(role in UserRoles for role in (InvestantMax, Developer)):
        # Check if this is DM
        if ctx.channel_id == UserDMChannel.id:
            UserSeesOnly = False

            # If this is an Investant Total Money Market Fund transaction, direct user to #itmm channel
            if itmm:
                await ctx.send(f"Please process all **Investant Total Money Market Fund** transactions in <#{InvestantTotalMoneyMarketFund}>.")
                return

            # MAIN
            with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
                try:
                    await BuyMainMethod(ctx, PaperTradeBot, UserSeesOnly, PaperTradeDB, UserID, InvestantServerID, CashFlow, InvestantTotalMoneyMarketFund, PaperTrade, quantity, ticker, itmm)
                except:
                    await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
                return
        
        elif ctx.channel.id not in [PaperTrade, InvestantTotalMoneyMarketFund]: # Wrong Channel
            # If this is an Investant Total Money Market Fund transaction, direct user to #itmm channel
            if itmm:
                await ctx.send(f"Please process all **Investant Total Money Market Fund** transactions in <#{InvestantTotalMoneyMarketFund}>.")
                return
            # Not itmm, so send them to #papertrade channel
            await ctx.send(f"This command is restricted to <#{PaperTrade}>.", ephemeral = True)
            return

        # MAIN
        UserSeesOnly = True
        with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
            try:
                await BuyMainMethod(ctx, PaperTradeBot, UserSeesOnly, PaperTradeDB, UserID, InvestantServerID, CashFlow, InvestantTotalMoneyMarketFund, PaperTrade, quantity, ticker, itmm)
            except:
                await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
            return

    # USER IS NOT DEVELOPER OR INVESTANTMAX
    UserSeesOnly = True
    if ctx.channel_id == UserDMChannel.id:
        UserSeesOnly = False
    await ctx.send(f"*I'm sorry, do I know you? Maybe you're friends with <@{PaperTradeBotID}>*", ephemeral = UserSeesOnly)
    return
# endregion

# region /sell command
@PaperTradeBot.command(
    name = "sell",
    description = "Sell an equity",
    options = [
        interactions.Option(
            name = "ticker",
            description = "the ticker symbol for the equity you would like to sell",
            type = interactions.OptionType.STRING,
            required = True
        ),
        interactions.Option(
            name = "quantity",
            description = "the quantity you would like to sell",
            type = interactions.OptionType.INTEGER,
            required = True,
            min_value = 1
        ),
        interactions.Option(
            name = "itmm",
            description = "optional: is this for the Investant Total Money Market Fund?",
            type = interactions.OptionType.BOOLEAN,
            required = False
        )
    ]
)
async def sell(ctx: interactions.CommandContext, ticker: str, quantity: int, itmm: bool = False):
    UserID = ctx.user.id

    if not await IsMemberInGuild(ctx, UserID, KeepingMembers):
        return

    GuildMember = KeepingMembers.GetMember(UserID)
    UserRoles = GuildMember.roles
    UserDMChannel = await GuildMember.user.get_dm_channel()

    # Check if user is InvestantMax
    if any(role in UserRoles for role in (InvestantMax, Developer)):
        # MAIN
        with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
            try:
                await SellMainMethod(ctx, PaperTradeBot, PaperTradeDB, UserID, InvestantServerID, InvestantTotalMoneyMarketFund, CashFlow, UserDMChannel, PaperTrade, quantity, ticker, itmm)
            except:
                await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
            return

    # USER IS NOT DEVELOPER OR INVESTANTMAX
    UserSeesOnly = True
    if ctx.channel_id == UserDMChannel.id:
        UserSeesOnly = False
    await ctx.send(f"*I'm sorry, do I know you? Maybe you're friends with <@{PaperTradeBotID}>*", ephemeral = UserSeesOnly)
    return
# endregion

# region /price command
@PaperTradeBot.command(
    name = "price",
    description = "Displays the price of an equity",
    options = [
        interactions.Option(
            name = "ticker",
            description = "the ticker symbol for the equity you would like the price of",
            type = interactions.OptionType.STRING,
            required = True
        )
    ]
)
async def price(ctx: interactions.CommandContext, ticker: str):
    UserID = ctx.user.id

    if not await IsMemberInGuild(ctx, UserID, KeepingMembers):
        return

    GuildMember = KeepingMembers.GetMember(UserID)
    UserRoles = GuildMember.roles
    UserDMChannel = await GuildMember.user.get_dm_channel()

    if any(role in UserRoles for role in (InvestantMax, Developer)):
        # Check if this is DM
        if ctx.channel_id == UserDMChannel.id:
            try: # MAIN
                await PriceMainMethod(ctx, ticker)
            except:
                await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
            return

        elif ctx.channel.id not in [PaperTrade, InvestantTotalMoneyMarketFund]: # Wrong Channel
            await ctx.send(f"This command is restricted to <#{PaperTrade}> and <#{InvestantTotalMoneyMarketFund}>.", ephemeral = True)
            return

        try: # MAIN
            await PriceMainMethod(ctx, ticker)
        except:
            await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
        return

    # USER IS NOT DEVELOPER OR INVESTANTMAX
    UserSeesOnly = True
    if ctx.channel_id == UserDMChannel.id:
        UserSeesOnly = False
    await ctx.send(f"*I'm sorry, do I know you? Maybe you're friends with <@{PaperTradeBotID}>*", ephemeral = UserSeesOnly)
    return
# endregion

# region /news command
@PaperTradeBot.command(
    name = "news",
    description = "DMs user current news about an equity",
    options = [
        interactions.Option(
            name = "ticker",
            description = "the ticker symbol for the equity you would like current news about",
            type = interactions.OptionType.STRING,
            required = True
        )
    ]
)
async def news(ctx: interactions.CommandContext, ticker: str):
    UserID = ctx.user.id

    if not await IsMemberInGuild(ctx, UserID, KeepingMembers):
        return

    GuildMember = KeepingMembers.GetMember(UserID)
    UserRoles = GuildMember.roles
    UserDMChannel = await GuildMember.user.get_dm_channel()

    # Check if user is InvestantMax
    if any(role in UserRoles for role in (InvestantMax, Developer)):
        # Check if this is DM
        if ctx.channel_id == UserDMChannel.id:
            DirectMessage = True
            try:
                await NewsMainMethod(ctx, GuildMember, ticker, DirectMessage)
            except:
                await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = False)
            return

        elif ctx.channel.id != PaperTrade: # Wrong Channel
            await ctx.send(f"This command is restricted to <#{PaperTrade}>.", ephemeral = True)
            return
        
        # MAIN
        DirectMessage = False
        try:
            await NewsMainMethod(ctx, GuildMember, ticker, DirectMessage)
        except:
            await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
        return

    # USER IS NOT DEVELOPER OR INVESTANTMAX
    UserSeesOnly = True
    if ctx.channel_id == UserDMChannel.id:
        UserSeesOnly = False
    await ctx.send(f"*I'm sorry, do I know you? Maybe you're friends with <@{PaperTradeBotID}>*", ephemeral = UserSeesOnly)
    return
# endregion

# region /revenue command
@PaperTradeBot.command(
    name = "revenue",
    description = "Sends revenue information about an equity",
    options = [
        interactions.Option(
            name = "ticker",
            description = "the ticker symbol for the equity you would like revenue information about",
            type = interactions.OptionType.STRING,
            required = True
        )
    ]
)
async def revenue(ctx: interactions.CommandContext, ticker: str):
    UserID = ctx.user.id

    if not await IsMemberInGuild(ctx, UserID, KeepingMembers):
        return

    GuildMember = KeepingMembers.GetMember(UserID)
    UserRoles = GuildMember.roles
    UserDMChannel = await GuildMember.user.get_dm_channel()

    # Check if user is InvestantMax
    if any(role in UserRoles for role in (InvestantMax, Developer)):
        # Check if this is DM
        if ctx.channel_id == UserDMChannel.id:
            try:
                await RevenueMainMethod(ctx, ticker)
            except:
                await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = False)
            return

        elif ctx.channel.id not in [PaperTrade, InvestantTotalMoneyMarketFund]: # Wrong Channel
            await ctx.send(f"This command is restricted to <#{PaperTrade}> and <#{InvestantTotalMoneyMarketFund}>.", ephemeral = True)
            return

        # MAIN
        try:
            await RevenueMainMethod(ctx, ticker)
        except:
            await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
        return

    # USER IS NOT DEVELOPER OR INVESTANT MAX
    UserSeesOnly = True
    if ctx.channel_id == UserDMChannel.id:
        UserSeesOnly = False
    await ctx.send(f"*I'm sorry, do I know you? Maybe you're friends with <@{PaperTradeBotID}>*", ephemeral = UserSeesOnly)
    return
# endregion

# region /bank command
@PaperTradeBot.command(
    name = "bank",
    description = "Sends user their current bank account balances"
)
async def bank(ctx: interactions.CommandContext):
    UserID = ctx.user.id

    if not await IsMemberInGuild(ctx, UserID, KeepingMembers):
        return

    GuildMember = KeepingMembers.GetMember(UserID)
    UserRoles = GuildMember.roles
    UserDMChannel = await GuildMember.user.get_dm_channel()

    if any(role in UserRoles for role in (InvestantMax, Developer)):
        # Check if this is DM
        if ctx.channel_id == UserDMChannel.id:
            UserSeesOnly = False
            with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
                try:
                    await BankMainMethod(ctx, PaperTradeDB, UserID, UserSeesOnly)
                except:
                    await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = UserSeesOnly)
                return

        # MAIN
        UserSeesOnly = True
        with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
            try:
                await BankMainMethod(ctx, PaperTradeDB, UserID, UserSeesOnly)
            except:
                await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = UserSeesOnly)
            return

    # USER IS NOT A DEVELOPER OR INVESTANT MAX
    UserSeesOnly = True
    if ctx.channel_id == UserDMChannel.id:
        UserSeesOnly = False
    await ctx.send(f"*I'm sorry, do I know you? Maybe you're friends with <@{PaperTradeBotID}>*", ephemeral = UserSeesOnly)
    return
# endregion

# region /transfer command
@PaperTradeBot.command(
    name = "transfer",
    description = "Transfer funds from [account1] to [account2]",
    options = [
        interactions.Option(
            name = "account1",
            description = "portfolio/checking/savings",
            type = interactions.OptionType.STRING,
            required = True,
            choices = [
                interactions.Choice(name = "portfolio", value = "portfolio"), interactions.Choice(name = "checking", value = "checking"), interactions.Choice(name = "savings", value = "savings")
            ]
        ),
        interactions.Option(
            name = "account2",
            description = "portfolio/checking/savings",
            type = interactions.OptionType.STRING,
            required = True,
            choices = [
                interactions.Choice(name = "portfolio", value = "portfolio"), interactions.Choice(name = "checking", value = "checking"), interactions.Choice(name = "savings", value = "savings")
            ]
        ),
        interactions.Option(
            name = "amount",
            description = "How much cash you want to transfer",
            type =interactions.OptionType.NUMBER,
            required = True,
            min_value = 0.01
        )
    ]
)
async def transfer(ctx: interactions.CommandContext, account1: str, account2: str, amount: float):
    withdraw, deposit = account1, account2
    UserID = ctx.user.id

    if not await IsMemberInGuild(ctx, UserID, KeepingMembers):
        return

    GuildMember = KeepingMembers.GetMember(UserID)
    UserRoles = GuildMember.roles
    UserDMChannel = await GuildMember.user.get_dm_channel()

    if any(role in UserRoles for role in (InvestantMax, Developer)):
        # Check if this is DM
        if ctx.channel_id == UserDMChannel.id:
            UserSeesOnly = False
            with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
                await ctx.defer(ephemeral = UserSeesOnly)
                try:
                    await TransferMainMethod(ctx, withdraw, deposit, amount, UserID, PaperTradeDB, PaperTradeBot, CashFlow, UserSeesOnly)
                except:
                    await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = UserSeesOnly)
                return

        # MAIN
        UserSeesOnly = True
        with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
            await ctx.defer(ephemeral = UserSeesOnly)
            try:
                await TransferMainMethod(ctx, withdraw, deposit, amount, UserID, PaperTradeDB, PaperTradeBot, CashFlow, UserSeesOnly)
            except:
                await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = UserSeesOnly)
            return

    # USER IS NOT DEVELOPER OR INVESTANT MAX
    UserSeesOnly = True
    if ctx.channel_id == UserDMChannel.id:
        UserSeesOnly = False
    await ctx.send(f"*I'm sorry, do I know you? Maybe you're friends with <@{PaperTradeBotID}>*", ephemeral = UserSeesOnly)
    return
# endregion

# region /pay command
@PaperTradeBot.command(
    name = "pay",
    description = "pay another user",
    options = [
        interactions.Option(
            name = "member",
            description = "the server member you would like to pay",
            type = interactions.OptionType.USER,
            required = True
        ),
        interactions.Option(
            name = "amount",
            description = "how much you would like to pay them",
            type = interactions.OptionType.NUMBER,
            required = True,
            min_value = 0.01
        )
    ]
)
async def pay(ctx: interactions.CommandContext, member: interactions.User, amount: float):
    UserID = ctx.user.id
    RecipientID = member.id

    if not await IsMemberInGuild(ctx, UserID, KeepingMembers):
        return

    GuildMember = KeepingMembers.GetMember(UserID)
    UserRoles = GuildMember.roles
    UserDMChannel = await GuildMember.user.get_dm_channel()
    InvestantGuild = await interactions.get(PaperTradeBot, interactions.Guild, object_id = InvestantServerID)
    AllGuildChannels = await InvestantGuild.get_all_channels()

    if any(role in UserRoles for role in (InvestantMax, Developer)):
        if ctx.channel not in AllGuildChannels: # If this message is outside of the Investant Server
            await ctx.send("*This is an Investant community command, please only use it within the Investant server.*")
            await ctx.send("https://discord.gg/SFUKKjWEjH")
            return
        
        elif member.bot:
            await ctx.send("You cannot pay a bot. We work for free.", ephemeral = True)
            return

        elif UserID == RecipientID: # User attempted to pay themself
            await ctx.send("As much as I want to do this for you... you can't pay yourself.", ephemeral = True)
            return

        # MAIN
        with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
            try:
                await PayMainMethod(ctx, PaperTradeBot, PaperTradeDB, UserID, RecipientID, amount, CashFlow)
            except:
                await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
            return

    # USER IS NOT DEVELOPER OR INVESTANT MAX
    UserSeesOnly = True
    if ctx.channel_id == UserDMChannel.id:
        UserSeesOnly = False
    await ctx.send(f"*I'm sorry, do I know you? Maybe you're friends with <@{PaperTradeBotID}>*", ephemeral = UserSeesOnly)
    return
# endregion

# region /itmm command
@PaperTradeBot.command(
    name = "itmm",
    description = "Investant Total Money Market Fund"
)
async def itmm(ctx: interactions.CommandContext):
    UserID = ctx.user.id

    if not await IsMemberInGuild(ctx, UserID, KeepingMembers):
        return

    GuildMember = KeepingMembers.GetMember(UserID)
    UserRoles = GuildMember.roles
    UserDMChannel = await GuildMember.user.get_dm_channel()

    if any(role in UserRoles for role in (InvestantMax, Developer)):
        if ctx.channel.id not in [PaperTrade, InvestantTotalMoneyMarketFund, UserDMChannel.id]: # Wrong Channel
            await ctx.send(f"This command is restricted to <#{PaperTrade}> and <#{InvestantTotalMoneyMarketFund}>.", ephemeral =True)
            return

        # MAIN
        with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
            await ctx.defer()
            try:
                await itmmMainMethod(ctx, PaperTradeDB, InvestantServerID, Gold = True)
            except:
                await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = False)
            return

    # USER IS NOT DEVELOPER OR INVESTANT MAX
    UserSeesOnly = True
    if ctx.channel_id == UserDMChannel.id:
        UserSeesOnly = False
    await ctx.send(f"*I'm sorry, do I know you? Maybe you're friends with <@{PaperTradeBotID}>*", ephemeral = UserSeesOnly)
    return
# endregion

# region /salary command
@PaperTradeBot.command(
    name = "salary",
    description = "Displays your current salary and pay"
)
async def salary(ctx: interactions.CommandContext):
    UserID = ctx.user.id

    if not await IsMemberInGuild(ctx, UserID, KeepingMembers):
        return

    GuildMember = KeepingMembers.GetMember(UserID)
    UserRoles = GuildMember.roles
    UserDMChannel = await GuildMember.user.get_dm_channel()
    UserSeesOnly = True

    if any(role in UserRoles for role in (InvestantMax, Developer)):
        # Check if this is DM
        if ctx.channel_id == UserDMChannel.id:
            UserSeesOnly = False
            with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
                try:
                    await SalaryMainMethod(ctx, PaperTradeDB, UserID, UserSeesOnly)
                except:
                    await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
                return
        
        # MAIN
        UserSeesOnly = True
        with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
            try:
                await SalaryMainMethod(ctx, PaperTradeDB, UserID, UserSeesOnly)
            except:
                await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
            return

    # USER IS NOT DEVELOPER OR INVESTANT MAX
    UserSeesOnly = True
    if ctx.channel_id == UserDMChannel.id:
        UserSeesOnly = False
    await ctx.send(f"*I'm sorry, do I know you? Maybe you're friends with <@{PaperTradeBotID}>*", ephemeral = UserSeesOnly)
    return
# endregion

# endregion /SLASH COMMANDS
# ------------------------------------------------------------------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# region DEPLOY BOT

# Bot Online - interactions
PaperTradeBot.start()

# endregion DEPLOY BOT
# ------------------------------------------------------------------------------------------------------------------------------------------------------------