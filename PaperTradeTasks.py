# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# region IMPORTS

import mysql.connector
from PaperTradeCommands import *
from PaperTradeEmbeds import *
from PaperTradeClasses import *
import interactions
import interactions.ext.files
import random

# endregion
# ------------------------------------------------------------------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# region MAINTENANCE TASKS

# Validate all discord members on startup
async def ValidateAllUsers(PaperTradeBot: interactions.Client, KeepingMembers: TrackingMembers, PaperTradeDB: mysql.connector.MySQLConnection, JobAssignment: int, PaperTrade: int):

    # Retrieve all discord members from the database
    DBCursor = PaperTradeDB.cursor() # Open Cursor
    DBCursor.execute("SELECT DISTINCT UserID FROM DiscordUserInfo ORDER BY UserID")
    Result = DBCursor.fetchall()
    AllListedUsers = [user[0] for user in Result]
    NewUsers = 0

    for member in KeepingMembers.AllMembers:

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
async def PayoutSalaries(PaperTradeDB: mysql.connector.MySQLConnection):
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

# Pay Daily Interest Accrual on Savings Accounts
async def PayoutSavingsInterest(PaperTradeDB: mysql.connector.MySQLConnection, AllMembers: list[interactions.Member], InvestantPlus: int, InvestantPro: int, InvestantMax: int):
    # Retrieve all Investant+, InvestantPro, and InvestantMax Users
    PlusMembers, ProMembers, MaxMembers = [], [], []
    for member in AllMembers:
        Roles = member.roles
        if InvestantPlus in Roles:
            PlusMembers.append(member.id)
        elif InvestantPro in Roles:
            ProMembers.append(member.id)
        elif InvestantMax in Roles:
            MaxMembers.append(member.id)

    # Keep Track of the Total Accrued Interest Paid
    TotalAccruedInterest = 0
    DBCursor = PaperTradeDB.cursor() # Open Cursor

    # For each Plus User, we need to calculate their accrued interest and make the payment
    PlusMembers = ','.join(str(user) for user in PlusMembers)
    DBCursor.execute(f"SELECT UserID, Savings FROM BankingAccounts WHERE UserID IN ({PlusMembers})")
    Result = DBCursor.fetchall()
    for UserID, Savings in Result:
        InterestPayment = round(Savings * 0.00008889427, 2) # Computed by taking 3.3% annual to a 4-year rate (y = (1 + 0.033)**4 - 1) then converting to a daily rate including leap years ((1 + y)**(1/1461) - 1)
        NewSavings = Savings + InterestPayment
        DBCursor.execute("UPDATE BankingAccounts SET Savings = %s WHERE UserID = %s", (NewSavings, UserID))
        TotalAccruedInterest += InterestPayment
    
    # For each Pro User, we need to calculate their accrued interest and make the payment
    ProMembers = ','.join(str(user) for user in ProMembers)
    DBCursor.execute(f"SELECT UserID, Savings FROM BankingAccounts WHERE UserID IN ({ProMembers})")
    Result = DBCursor.fetchall()
    for UserID, Savings in Result:
        InterestPayment = round(Savings * 0.00010211551, 2) # Computed by taking 3.8% annual to a 4-year rate (y = (1 + 0.038)**4 - 1) then converting to a daily rate including leap years ((1 + y)**(1/1461) - 1)
        NewSavings = Savings + InterestPayment
        DBCursor.execute("UPDATE BankingAccounts SET Savings = %s WHERE UserID = %s", (NewSavings, UserID))
        TotalAccruedInterest += InterestPayment

    # For each Max User, we need to calculate their accrued interest and make the payment
    MaxMembers = ','.join(str(user) for user in MaxMembers)
    DBCursor.execute(f"SELECT UserID, Savings FROM BankingAccounts WHERE UserID IN ({MaxMembers})")
    Result = DBCursor.fetchall()
    for UserID, Savings in Result:
        InterestPayment = round(Savings * 0.0001205189, 2) # Computed by taking 4.5% annual to a 4-year rate (y = (1 + 0.045)**4 - 1) then converting to a daily rate including leap years ((1 + y)**(1/1461) - 1)
        NewSavings = Savings + InterestPayment
        DBCursor.execute("UPDATE BankingAccounts SET Savings = %s WHERE UserID = %s", (NewSavings, UserID))
        TotalAccruedInterest += InterestPayment

    # Commit these changes and close the cursor
    PaperTradeDB.commit()
    DBCursor.close() # Close Cursor

    # Generate the embed and files to send to General Channel
    embed, files = GenerateSavingsInterest(TotalAccruedInterest)
    # RETURN EMBED AND FILES
    return embed, files

# Handle new entrant to the Investant server
async def NewMemberJoined(member: interactions.Member, PaperTradeDB: mysql.connector.MySQLConnection, PaperTradeBot: interactions.Client, PaperTrade: int, JobAssignment: int, KeepingMembers: TrackingMembers):
    # Grab UserID of discord member and add to AllMembers list
    KeepingMembers.AddMember(member)
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
def GetRoleID(Job: str):
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
async def IsMemberInGuild(ctx: interactions.CommandContext, UserID: int, KeepingMembers: TrackingMembers):
    for member in KeepingMembers.AllMembers:
        if member.id == UserID:
            print("Found You in Members Object")
            return True
    await ctx.send(f"I'm sorry, I don't seem to recall knowing you... Feel free to join!")
    await ctx.send("https://discord.gg/SFUKKjWEjH")
    return False

# endregion MAINTENANCE
# ------------------------------------------------------------------------------------------------------------------------------------------------------------