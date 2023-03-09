# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# region IMPORTS

from PaperTradeCommands import *
from PaperTradeEmbeds import *
import interactions
import interactions.ext.files
import random

# endregion
# ------------------------------------------------------------------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# region MAINTENANCE TASKS

# Validate all discord members on startup
async def ValidateAllUsers(PaperTradeBot, InvestantServerID, PaperTradeDB, JobAssignment, PaperTrade):

    # Retrieve all discord members from the discord
    InvestantGuild = await interactions.get(PaperTradeBot, interactions.Guild, object_id = InvestantServerID)
    AllMembers = await InvestantGuild.get_all_members()

    # Retrieve all discord members from the database
    DBCursor = PaperTradeDB.cursor() # Open Cursor
    DBCursor.execute("SELECT DISTINCT UserID FROM DiscordUserInfo ORDER BY UserID")
    Result = DBCursor.fetchall()
    AllListedUsers = [user[0] for user in Result]
    NewUsers = 0

    for member in AllMembers:

        if member.user.bot: # If this is a bot, skip
            continue

        UserID = str(member.id)
        if BinarySearch(List = AllListedUsers, Value = UserID): # Returns true if found
            continue

        else:
            # Give user a job and salary
            Job, Salary = GiveJob()
            RoleID = GetRoleID(Job)

            # Add the appropriate role to the new member
            await member.add_role(role = RoleID)

            # Update DiscordUserInfo table in PaperTradeDB database with UserID, Job, and Salary
            DBCursor.execute("INSERT INTO DiscordUserInfo (UserID, Job, Salary) VALUES (%s, %s, %s)", (UserID, Job, Salary))
            # Update PortfolioHoldings table in PaperTradeDB database with their starting Cash Account
            # Cash Balance string value in Holding field "Cash Balance"
            SignOnBonus = round(Salary / 10, 2)
            DBCursor.execute("INSERT INTO PortfolioHoldings (UserID, Holding, TotalCost) VALUES (%s, %s, %s)", (UserID, "Cash Balance", SignOnBonus))
            # Cash Proceeds for record keeping value in Holding field "Cash Proceeds"
            DBCursor.execute("INSERT INTO PortfolioHoldings (UserID, Holding, TotalCost) VALUES (%s, %s, %s)", (UserID, "Cash Proceeds", 0))
            # Create Checking and Savings accounts for User
            DBCursor.execute("INSERT INTO BankingAccounts (UserID, Checking, Savings) VALUES (%s, %s, %s)", (UserID, 0, 0))

            JobAssignmentChannel = await interactions.get(PaperTradeBot, interactions.Channel, object_id = JobAssignment)

            # Send Welcome Prompt
            prompt = NewMemberPrompt(member, Job, Salary, SignOnBonus, PaperTrade)
            await member.user.send(prompt)
            await JobAssignmentChannel.send(f"Hey <@{member.id}>, congratulations on your new position as a **{Job}**!")
            NewUsers += 1

    # Commit changes to the PaperTradeDB database
    PaperTradeDB.commit()
    DBCursor.close() # Close Cursor
    return NewUsers

# Payout Salaries Event Method
def PayoutSalaries(PaperTradeDB):
    # Retrieve all discord members with jobs in the database
    DBCursor = PaperTradeDB.cursor() # Open Cursor
    DBCursor.execute("SELECT DISTINCT UserID, Salary FROM DiscordUserInfo")
    MemberSelection = DBCursor.fetchall()
    NumEmployees = len(MemberSelection)
    TotalPayout = 0

    for member in MemberSelection: # Process salary payments to user accounts
        UserID, UserSalary = member[0], member[1]

        # We need to know their checking balance as well
        DBCursor.execute("SELECT Checking FROM BankingAccounts WHERE UserID = %s", [UserID])
        UserCheckingBalance = DBCursor.fetchone()[0]

        # Calculate payment and new checking balance
        # 0.01916496 derives from 1461 days in a 4-year period with leap years, divided by 28 (7 days/week * 4 years)
        Payment = round(UserSalary * 0.01916496, 2) # Weekly Payment
        TotalPayout += Payment
        NewCheckingBalance = round(UserCheckingBalance + Payment, 2)

        # Update their checking balance
        DBCursor.execute("UPDATE BankingAccounts SET Checking = %s WHERE UserID = %s", (NewCheckingBalance, UserID))
    
    # Commite these changes to the database
    PaperTradeDB.commit()
    DBCursor.close() # Close Cursor

    embed, files = GenerateSalaryPayoutEmbed(NumEmployees, TotalPayout)
    return embed, files

# Handle new entrant to the Investant server
async def NewMemberJoined(member, PaperTradeDB, PaperTradeBot, PaperTrade, JobAssignment):
    # Grab UserID of discord member
    UserID = member.user.id
    DBCursor = PaperTradeDB.cursor() # Open Cursor
    DBCursor.execute("SELECT * FROM DiscordUserInfo where UserID = %s", [str(UserID)])

    if len(DBCursor.fetchall()) > 0: # This user has already been in the server and has a portfolio

        DBCursor.execute("SELECT Job FROM DiscordUserInfo where UserID = %s", [str(UserID)]) # Fetch User's Job
        Job = DBCursor.fetchone()[0]
        DBCursor.execute("SELECT TotalCost FROM PortfolioHoldings WHERE UserID = %s AND Holding = %s", (str(UserID), "Cash Balance")) # Fetch User's Cash Balance
        UserCashTotal = DBCursor.fetchone()[0]
        DBCursor.execute("SELECT Checking, Savings FROM BankingAccounts WHERE UserID = %s", [str(UserID)])
        BankAccounts = DBCursor.fetchone()
        UserChecking = BankAccounts[0]
        UserSavings = BankAccounts[1]
        DBCursor.close() # Close Cursor

        # Reassign job role to user
        RoleID = GetRoleID(Job)
        await member.add_role(role = RoleID)

        # Send welcome back DM
        message = ReturningUserMessage(member, Job, UserCashTotal, UserChecking, UserSavings, PaperTrade)
        await member.user.send(message)
        return

    # Give user a job and salary
    Job, Salary = GiveJob()
    RoleID = GetRoleID(Job)

    # Add the appropriate role to the new member
    await member.add_role(role = RoleID)

    # Update DiscordUserInfo table in PaperTradeDB database with UserID, Job, and Salary
    DBCursor.execute("INSERT INTO DiscordUserInfo (UserID, Job, Salary) VALUES (%s, %s, %s)", (str(UserID), Job, Salary))
    # Update PortfolioHoldings table in PaperTradeDB database with their starting Cash Account
    # Cash Balance string value in Holding field "Cash Balance"
    SignOnBonus = round(Salary / 10, 2)
    DBCursor.execute("INSERT INTO PortfolioHoldings (UserID, Holding, TotalCost) VALUES (%s, %s, %s)", (str(UserID), "Cash Balance", SignOnBonus))
    # Cash Proceeds for record keeping value in Holding field "Cash Proceeds"
    DBCursor.execute("INSERT INTO PortfolioHoldings (UserID, Holding, TotalCost) VALUES (%s, %s, %s)", (str(UserID), "Cash Proceeds", 0))
    # Create Checking and Savings accounts for User
    DBCursor.execute("INSERT INTO BankingAccounts (UserID, Checking, Savings) VALUES (%s, %s, %s)", (str(UserID), 0, 0))
    # Process changes to the PaperTradeDB database
    PaperTradeDB.commit()
    DBCursor.close() # Close Cursor

    JobAssignmentChannel = await interactions.get(PaperTradeBot, interactions.Channel, object_id = JobAssignment)

    # Send Welcome Prompt
    prompt = NewMemberPrompt(member, Job, Salary, SignOnBonus, PaperTrade)
    await member.user.send(prompt)
    await JobAssignmentChannel.send(f"Hey <@{UserID}>, congratulations on your new position as a **{Job}**!")
    return

# Generate random job and salary for discord user
def GiveJob():
    Jobs = {
        "Plumber": (52000, 88000),
        "Traveling Circus Clown": (41000, 64000),
        "Salesperson at CarMax": (41000, 64000),
        "Social Media Influencer": (44000, 180000),
        "Nurse": (52000, 88000),
        "Lawyer": (90000, 170000),
        "Carpenter": (52000, 88000),
        "Fast-Food Employee": (41000, 64000),
        "General Surgeon": (125000, 205000),
        "Data Engineer": (90000, 170000),
        "Software Developer": (90000, 170000),
        "Financial Analyst": (90000, 170000),
        "Commercial Pilot": (125000, 205000),
        "Entrepreneur": (44000, 180000),
        "Politician": (115000, 150000)
    }
    Job = random.choice(Jobs.keys())
    SalaryRange = Jobs[Job]
    Salary = random.randint(SalaryRange[0], SalaryRange[1])
    return Job, Salary

# Retrieve the ID for the Role of the user's job in the discord server
def GetRoleID(Job):
    RoleIDs = {
        "Plumber": 1076732217994264717,
        "Traveling Circus Clown": 1076732406553399336,
        "Salesperson at CarMax": 1076732453714141194,
        "Social Media Influencer": 1076732485238521896,
        "Nurse": 1076732506625277992,
        "Lawyer": 1076732533976338486,
        "Carpenter": 1076732549801443338,
        "Fast-Food Employee": 1076732568621305877,
        "General Surgeon": 1076732584727429180,
        "Data Engineer": 1076732604432265298,
        "Software Developer": 1076732621452746852,
        "Financial Analyst": 1076732640910131220,
        "Commercial Pilot": 1076732667929821234,
        "Entrepreneur": 1076732685449441341,
        "Politician": 1076732702235033660
    }
    return RoleIDs[Job]

# Check if user is in the Investant server
async def IsMemberInGuild(ctx, UserID, InvestantServerID, PaperTradeBot):
    InvestantGuild = await interactions.get(PaperTradeBot, interactions.Guild, object_id = InvestantServerID)
    AllMembers = await InvestantGuild.get_all_members()
    for member in AllMembers:
        if member.id == UserID:
            return True
    await ctx.send(f"I'm sorry, I don't seem to recall knowing you... Feel free to join!")
    await ctx.send("https://discord.gg/SFUKKjWEjH")
    return False


# endregion MAINTENANCE
# ------------------------------------------------------------------------------------------------------------------------------------------------------------