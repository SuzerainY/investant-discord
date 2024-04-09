# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# region IMPORTS

from PaperTradeCommands import *
from PaperTradeTasks import *
from PaperTradeClasses import *
from datetime import datetime
from pytz import timezone
from interactions.ext.tasks import IntervalTrigger, create_task
import interactions
import interactions.ext.files
import mysql.connector
import contextlib
import time
import os

dbhost = os.environ.get("PTDBHOST")
dbuser = os.environ.get("PTDBUSER")
dbpasswd = os.environ.get("PTDBPASSWD")
db = os.environ.get("PTDB")
InvestantServerID = os.environ.get("PTINVESTANTSERVERID")
BotToken = os.environ.get("PTBOTTOKEN")

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

# Keep track of all online members
KeepingMembers = TrackingMembers()

# Bot IDs
PaperTradeBotID = 1075539986453119086
PaperTradeGoldBotID = 1076566586158239796

# Channel IDs
JobAssignment = 1077003046724309134
CashFlow = 1076568911216115712
PaperTrade = 1075555630296870932
InvestantTotalMoneyMarketFund = 1075589065606451250
General = 1075472790972547242
Announcements = 1076353593743003648

# Role IDs
InvestantPlus = 1075629267842514964
InvestantPro = 1075617181175402557
InvestantMax = 1075603607354867732
InvestantGroup = 1075463305637920930
Developer = 1075547410027257956

# Create the bot
PaperTradeBot = interactions.Client(
    token = BotToken,
    scope = InvestantServerID,
    intents = interactions.Intents.DEFAULT | interactions.Intents.GUILD_MESSAGE_CONTENT | interactions.Intents.GUILD_MEMBERS
)
# endregion Login and Startup
# ------------------------------------------------------------------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# region TASKS | DEFINE TASKS TO EXECUTE AT RUNTIME
class TasksCog(interactions.Extension):
    def __init__(self, PaperTradeBot):
        self.PaperTradeBot: interactions.Client = PaperTradeBot
        self.SalariesAlreadyPaid = False
        self.SavingsInterestPaid = False

    # PAYOUT SALARIES WEEKLY AT 5:00PM EST EACH FRIDAY
    @create_task(IntervalTrigger(300)) # runs every 5 minutes
    async def SalaryPayouts(self):
        # What time is it right now
        EasternStandardTimeZone = timezone('EST')
        TimeRightNow = datetime.now(EasternStandardTimeZone)

        if (TimeRightNow.isoweekday() == 5) and (TimeRightNow.hour == 17) and (TimeRightNow.minute <= 6):
            if not self.SalariesAlreadyPaid:
                
                # Payout salaries to all users
                with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
                    print("TASK: Paying Salaries")
                    embed, files = await PayoutSalaries(PaperTradeDB)
                    print("TASK COMPLETE: Salaries Paid")

                self.SalariesAlreadyPaid = True
                AnnouncementsChannel = await interactions.get(PaperTradeBot, interactions.Channel, object_id = Announcements)
                await AnnouncementsChannel.send(embeds=embed, files=files)

        elif (TimeRightNow.isoweekday() == 5) and (TimeRightNow.hour == 17) and (TimeRightNow.minute > 6):
            self.SalariesAlreadyPaid = False
    
    # PAYOUT SAVINGS DAILY AT 4:00PM EST
    @create_task(IntervalTrigger(600)) # runs every 10 minutes
    async def SavingsInterestPayouts(self):
        # What time is it right now
        EasternStandardTimeZone = timezone('EST')
        TimeRightNow = datetime.now(EasternStandardTimeZone)

        if (TimeRightNow.hour == 16) and (TimeRightNow.minute <= 11):
            if not self.SavingsInterestPaid:

                # Fetch All Members
                InvestantGuild = await interactions.get(PaperTradeBot, interactions.Guild, object_id = InvestantServerID)
                AllMembers = await InvestantGuild.get_all_members()

                # Payout Interest to all Investant+, InvestantPro, and InvestantMax users
                with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
                    print("TASK: Paying Accrued Savings Interest")
                    embed, files = await PayoutSavingsInterest(PaperTradeDB, AllMembers, InvestantPlus, InvestantPro, InvestantMax)
                    print("TASK COMPLETE: Accrued Savings Interest Paid")
                
                self.SavingsInterestPaid = True
                if embed: # embed will be None if there were no users to pay interest to, so we will not send message | will contain embedded message to send otherwise
                    AnnouncementsChannel = await interactions.get(PaperTradeBot, interactions.Channel, object_id = Announcements)
                    await AnnouncementsChannel.send(embeds=embed, files=files)
            
        elif (TimeRightNow.hour == 16) and (TimeRightNow.minute > 11):
            self.SavingsInterestPaid = False

# endregion TASKS
# ------------------------------------------------------------------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# region EVENT COMMANDS | DEFINE EVENTS WHICH SHOULD RUN ON TRIGGER

# region Application Startup
@PaperTradeBot.event
async def on_start():
    time.sleep(2)

    # Fetch All Members
    InvestantGuild = await interactions.get(PaperTradeBot, interactions.Guild, object_id = InvestantServerID)
    AllMembers = await InvestantGuild.get_all_members()
    KeepingMembers.InitiateAllMembers(AllMembers)

    # Validate any new users who joined while bot was offline
    with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
        print("PaperTrade is now online. Validating all discord members exist in database.")
        NewUsers = await ValidateAllUsers(PaperTradeBot, KeepingMembers, PaperTradeDB, JobAssignment, PaperTrade)
        print(f"All discord members validated. There were {NewUsers} new members to process.")

    # Start Tasks
    TasksCogInstance = TasksCog(PaperTradeBot)
    TasksCog.SalaryPayouts.start(TasksCogInstance)
    TasksCog.SavingsInterestPayouts.start(TasksCogInstance)
    return
# endregion

# region New Member Joined
@PaperTradeBot.event
async def on_guild_member_add(member: interactions.GuildMember):
    with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
        await NewMemberJoined(member, PaperTradeDB, PaperTradeBot, PaperTrade, JobAssignment, KeepingMembers)
        print(f"New Member {member.name} Joined. Successfully Added To Database. UserID: {member.id}")
        return
# endregion

# endregion EVENT COMMANDS
# ------------------------------------------------------------------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# region /SLASH COMMANDS | DEFINE ALL /SLASH COMMANDS FOR USE WITHIN THE INVESTANT SERVER

# region /help command
@PaperTradeBot.command(
    name = "help",
    description = f"Sends a list of all possible user commands with PaperTradeGOLD",
)
async def help(ctx: interactions.CommandContext):
    UserID = ctx.user.id

    if not await IsMemberInGuild(ctx, UserID, KeepingMembers):
        return

    GuildMember = KeepingMembers.GetMember(UserID)
    UserRoles = GuildMember.roles
    UserDMChannel = await GuildMember.user.get_dm_channel()
    # Check is this is a DM
    UserSeesOnly = True
    if ctx.channel_id == UserDMChannel.id:
        UserSeesOnly = False

    # Check if user is Max
    if InvestantMax in UserRoles:
        await ctx.send(f"*Gracious InvestantMax user, why trouble yourself with me when you have the spectacular <@{PaperTradeGoldBotID}>...*", ephemeral = UserSeesOnly)
        return

    try: # MAIN
        embed, files = HelpEmbed(Gold = False)
        await ctx.send(embeds = embed, files = files)
    except:
        await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
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
    UserSeesOnly = True

    # Check if user is Max
    if InvestantMax in UserRoles:
        # Check is this is a DM
        if ctx.channel_id == UserDMChannel.id:
            UserSeesOnly = False
        await ctx.send(f"*Gracious InvestantMax user, why trouble yourself with me when you have the spectacular <@{PaperTradeGoldBotID}>...*", ephemeral = UserSeesOnly)
        return

    # Check if this is DM
    elif ctx.channel_id == UserDMChannel.id:
        UserSeesOnly = False

        # Check if user is Plus or Pro
        if any(role in UserRoles for role in (InvestantPlus, InvestantPro, Developer)):
            # MAIN PORTFOLIO METHOD
            with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
                await ctx.defer(ephemeral = UserSeesOnly)
                try:
                    await MainPortfolioMethod(ctx, PaperTradeDB, UserID, UserSeesOnly, Gold = False)
                except:
                    await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = UserSeesOnly)
                return

        await ctx.send(f"If you would like to use this command in private channels, please upgrade your subscription to **Investant+** or higher.")
        return

    # This is not a DM
    elif ctx.channel.id != PaperTrade:
        await ctx.send(f"This command is restricted to <#{PaperTrade}>.", ephemeral = True)
        return

    # MAIN PORTFOLIO METHOD
    UserSeesOnly = True
    with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
        await ctx.defer(ephemeral = UserSeesOnly)
        try:
            await MainPortfolioMethod(ctx, PaperTradeDB, UserID, UserSeesOnly, Gold = False)
        except:
            await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = UserSeesOnly)
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
        )
    ]
)
async def buy(ctx: interactions.CommandContext, ticker: str, quantity: int):
    UserID = ctx.user.id

    if not await IsMemberInGuild(ctx, UserID, KeepingMembers):
        return

    GuildMember = KeepingMembers.GetMember(UserID)
    UserRoles = GuildMember.roles
    UserDMChannel = await GuildMember.user.get_dm_channel()
    UserSeesOnly = True

    # Check if user is Max
    if InvestantMax in UserRoles:
        # Check is this is a DM
        if ctx.channel_id == UserDMChannel.id:
            UserSeesOnly = False
        await ctx.send(f"*Gracious InvestantMax user, why trouble yourself with me when you have the spectacular <@{PaperTradeGoldBotID}>...*", ephemeral = UserSeesOnly)
        return

    # Check if this is DM
    elif ctx.channel_id == UserDMChannel.id:

        UserSeesOnly = False

        # Check if user is Plus or Pro
        if any(role in UserRoles for role in (InvestantPlus, InvestantPro, Developer)):
            # MAIN
            with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
                try:
                    await BuyMainMethod(ctx, PaperTradeBot, UserSeesOnly, PaperTradeDB, UserID, InvestantServerID, CashFlow, InvestantTotalMoneyMarketFund, PaperTrade, quantity, ticker, False)
                except:
                    await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True) 
                return

        # Normal User and attempted to DM bot
        await ctx.send(f"If you would like to use this command in private channels, please upgrade your subscription to **Investant+** or higher.")
        return
    
    elif ctx.channel.id != PaperTrade: # Normal User, Not a DM, but not in #PaperTrade channel
        await ctx.send(f"This command is restricted to <#{PaperTrade}>.", ephemeral = True)
        return

    # MAIN
    UserSeesOnly = True
    with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
        try:
            await BuyMainMethod(ctx, PaperTradeBot, UserSeesOnly, PaperTradeDB, UserID, InvestantServerID, CashFlow, InvestantTotalMoneyMarketFund, PaperTrade, quantity, ticker, False)
        except:
            await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
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
        )
    ]
)
async def sell(ctx: interactions.CommandContext, ticker: str, quantity: int):
    UserID = ctx.user.id

    if not await IsMemberInGuild(ctx, UserID, KeepingMembers):
        return

    GuildMember = KeepingMembers.GetMember(UserID)
    UserRoles = GuildMember.roles
    UserDMChannel = await GuildMember.user.get_dm_channel()
    UserSeesOnly = True

    # Check if user is Max
    if InvestantMax in UserRoles:
        # Check is this is a DM
        if ctx.channel_id == UserDMChannel.id:
            UserSeesOnly = False
        await ctx.send(f"*Gracious InvestantMax user, why trouble yourself with me when you have the spectacular <@{PaperTradeGoldBotID}>...*", ephemeral = UserSeesOnly)
        return

    # Check if this is DM
    elif ctx.channel_id == UserDMChannel.id:

        # Check if user is Plus or Pro
        if any(role in UserRoles for role in (InvestantPlus, InvestantPro, Developer)):
            with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
                try:
                    await SellMainMethod(ctx, PaperTradeBot, PaperTradeDB, UserID, InvestantServerID, InvestantTotalMoneyMarketFund, CashFlow, UserDMChannel, PaperTrade, quantity, ticker, False)
                except:
                    await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
                return

        # Normal User attempted to DM Bot
        await ctx.send(f"If you would like to use this command in private channels, please upgrade your subscription to **Investant+** or higher.")
        return

    if ctx.channel.id != PaperTrade: # Normal User, Not a DM, but not in #PaperTrade channel
        await ctx.send(f"This command is restricted to <#{PaperTrade}>.", ephemeral = True)
        return

    # MAIN
    with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
        try:
            await SellMainMethod(ctx, PaperTradeBot, PaperTradeDB, UserID, InvestantServerID, InvestantTotalMoneyMarketFund, CashFlow, UserDMChannel, PaperTrade, quantity, ticker, False)
        except:
            await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
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
    UserSeesOnly = True

    # Check if user is Max
    if InvestantMax in UserRoles:
        # Check is this is a DM
        if ctx.channel_id == UserDMChannel.id:
            UserSeesOnly = False
        await ctx.send(f"*Gracious InvestantMax user, why trouble yourself with me when you have the spectacular <@{PaperTradeGoldBotID}>...*", ephemeral = UserSeesOnly)
        return

    # Check if this is DM
    elif ctx.channel_id == UserDMChannel.id:

        # Check if user is Plus or Pro
        if any(role in UserRoles for role in (InvestantPlus, InvestantPro, Developer)):
            try:
                await PriceMainMethod(ctx, ticker)
            except:
                await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
            return
        
        # Normal User attempted to DM bot
        await ctx.send(f"If you would like to use this command in private channels, please upgrade your subscription to **Investant+** or higher.")
        return

    elif ctx.channel.id != PaperTrade:
        await ctx.send(f"This command is restricted to <#{PaperTrade}>.", ephemeral = True)
        return

    try: # MAIN
        await PriceMainMethod(ctx, ticker)
    except:
        await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
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
    UserSeesOnly = True

    # Check if user is Max
    if InvestantMax in UserRoles:
        # Check is this is a DM
        if ctx.channel_id == UserDMChannel.id:
            UserSeesOnly = False
        await ctx.send(f"*Gracious InvestantMax user, why trouble yourself with me when you have the spectacular <@{PaperTradeGoldBotID}>...*", ephemeral = UserSeesOnly)
        return

    # Check if this is DM
    elif ctx.channel_id == UserDMChannel.id:
        DirectMessage = True
        # Check if user is Plus or Pro
        if any(role in UserRoles for role in (InvestantPlus, InvestantPro, Developer)):
            try:
                await NewsMainMethod(ctx, GuildMember, ticker, DirectMessage)
            except:
                await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
            return
        
        await ctx.send(f"If you would like to use this command in private channels, please upgrade your subscription to **Investant+** or higher.")
        return

    elif ctx.channel.id != PaperTrade:
        await ctx.send(f"This command is restricted to <#{PaperTrade}>.", ephemeral = True)
        return
    
    # MAIN
    DirectMessage = False
    try:
        await NewsMainMethod(ctx, GuildMember, ticker, DirectMessage)
    except:
        await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
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
    UserSeesOnly = True

    # Check if user is Max
    if InvestantMax in UserRoles:
        # Check is this is a DM
        if ctx.channel_id == UserDMChannel.id:
            UserSeesOnly = False
        await ctx.send(f"*Gracious InvestantMax user, why trouble yourself with me when you have the spectacular <@{PaperTradeGoldBotID}>...*", ephemeral = UserSeesOnly)
        return

    # Check if this is DM
    elif ctx.channel_id == UserDMChannel.id:

        # Check if user is Plus or Pro
        if any(role in UserRoles for role in (InvestantPlus, InvestantPro, Developer)):
            try:
                await RevenueMainMethod(ctx, ticker)
            except:
                await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
            return

        await ctx.send(f"If you would like to use this command in private channels, please upgrade your subscription to **Investant+** or higher.")
        return

    elif ctx.channel.id != PaperTrade:
        await ctx.send(f"This command is restricted to <#{PaperTrade}>.", ephemeral = True)
        return

    try: # MAIN
        await RevenueMainMethod(ctx, ticker)
    except:
        await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
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
    UserSeesOnly = True

    # Check if user is Max
    if InvestantMax in UserRoles:
        # Check is this is a DM
        if ctx.channel_id == UserDMChannel.id:
            UserSeesOnly = False
        await ctx.send(f"*Gracious InvestantMax user, why trouble yourself with me when you have the spectacular <@{PaperTradeGoldBotID}>...*", ephemeral = UserSeesOnly)
        return

    # Check if this is DM
    elif ctx.channel_id == UserDMChannel.id:
        UserSeesOnly = False

        # Check if user is Plus or Pro
        if any(role in UserRoles for role in (InvestantPlus, InvestantPro, Developer)):
            with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
                try:
                    await BankMainMethod(ctx, PaperTradeDB, UserID, UserSeesOnly)
                except:
                    await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
                return

        await ctx.send(f"If you would like to use this command in private channels, please upgrade your subscription to **Investant+** or higher.")
        return

    # MAIN
    UserSeesOnly = True
    with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
        try:
            await BankMainMethod(ctx, PaperTradeDB, UserID, UserSeesOnly)
        except:
            await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
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

    withdraw, deposit = account1, account2 # syntax used below prepared
    UserID = ctx.user.id

    if not await IsMemberInGuild(ctx, UserID, KeepingMembers):
        return

    GuildMember = KeepingMembers.GetMember(UserID)
    UserRoles = GuildMember.roles
    UserDMChannel = await GuildMember.user.get_dm_channel()
    UserSeesOnly = True

    # Check if user is Max
    if InvestantMax in UserRoles:
        # Check is this is a DM
        if ctx.channel_id == UserDMChannel.id:
            UserSeesOnly = False
        await ctx.send(f"*Gracious InvestantMax user, why trouble yourself with me when you have the spectacular <@{PaperTradeGoldBotID}>...*", ephemeral = UserSeesOnly)
        return

    # Check if this is DM
    elif ctx.channel_id == UserDMChannel.id:

        # Check if user is Plus or Pro
        if any(role in UserRoles for role in (InvestantPlus, InvestantPro, Developer)):
            UserSeesOnly = False
            with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
                await ctx.defer(ephemeral = UserSeesOnly)
                try:
                    await TransferMainMethod(ctx, withdraw, deposit, amount, UserID, PaperTradeDB, PaperTradeBot, CashFlow, UserSeesOnly)
                except:
                    await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = UserSeesOnly)
                return
        await ctx.send(f"If you would like to use this command in private channels, please upgrade your subscription to **Investant+** or higher.")
        return

    else: # MAIN
        UserSeesOnly = True
        with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
            await ctx.defer(ephemeral = UserSeesOnly)
            try:
                await TransferMainMethod(ctx, withdraw, deposit, amount, UserID, PaperTradeDB, PaperTradeBot, CashFlow, UserSeesOnly)
            except:
                await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = UserSeesOnly)
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
    UserSeesOnly = True

    # Check if user is Max
    if InvestantMax in UserRoles:
        # Check is this is a DM
        if ctx.channel_id == UserDMChannel.id:
            UserSeesOnly = False
        await ctx.send(f"*Gracious InvestantMax user, why trouble yourself with me when you have the spectacular <@{PaperTradeGoldBotID}>...*", ephemeral = UserSeesOnly)
        return

    elif ctx.channel not in AllGuildChannels: # If this message is outside of the Investant Server
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
    UserSeesOnly = True

    # Check if user is Max
    if InvestantMax in UserRoles:
        # Check is this is a DM
        if ctx.channel_id == UserDMChannel.id:
            UserSeesOnly = False
        await ctx.send(f"*Gracious InvestantMax user, why trouble yourself with me when you have the spectacular <@{PaperTradeGoldBotID}>...*", ephemeral = UserSeesOnly)
        return

    elif ctx.channel_id not in [PaperTrade, InvestantTotalMoneyMarketFund, UserDMChannel.id]: # Wrong Channel
        await ctx.send(f"This command is restricted to <#{PaperTrade}> and <#{InvestantTotalMoneyMarketFund}>.", ephemeral = True)
        return

    # I allow all users to receive the /itmm in direct messages because we want to promote the Investant Total Money Market Fund
    with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
        await ctx.defer()
        try:
            await itmmMainMethod(ctx, PaperTradeDB, InvestantServerID, Gold = False)
        except:
            await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = UserSeesOnly)
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

    # Check if user is Max
    if InvestantMax in UserRoles:
        # Check is this is a DM
        if ctx.channel_id == UserDMChannel.id:
            UserSeesOnly = False
        await ctx.send(f"*Gracious InvestantMax user, why trouble yourself with me when you have the spectacular <@{PaperTradeGoldBotID}>...*", ephemeral = UserSeesOnly)
        return

    # Check if this is DM
    elif ctx.channel_id == UserDMChannel.id:
        UserSeesOnly = False

        # Check if user is Plus or Pro
        if any(role in UserRoles for role in (InvestantPlus, InvestantPro, Developer)):
            with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
                try:
                    await SalaryMainMethod(ctx, PaperTradeDB, UserID, UserSeesOnly)
                except:
                    await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
                return

        await ctx.send(f"If you would like to use this command in private channels, please upgrade your subscription to **Investant+** or higher.")
        return
    
    # MAIN
    UserSeesOnly = True
    with ConnectToPaperTradeDB(dbhost, dbuser, dbpasswd, db) as PaperTradeDB:
        try:
            await SalaryMainMethod(ctx, PaperTradeDB, UserID, UserSeesOnly)
        except:
            await ctx.send("An error occurred. If this persists, please contact management.", ephemeral = True)
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