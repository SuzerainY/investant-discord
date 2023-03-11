import interactions

class TrackingMembers:
    def __init__(self):
        self.AllMembers = None

    def InitiateAllMembers(self, AllMembers: list[interactions.Member]):
        self.AllMembers = AllMembers
        return
    
    def AddMember(self, member: interactions.Member):
        if not self.AllMembers:
            return
        self.AllMembers.append(member)
        return
    
    def GetMember(self, UserID: int):
        for member in self.AllMembers:
            if member.id == UserID:
                return member
        print("Member not found in TrackingMembers Object. Method [TrackingMembers.GetMember()] failed")
        return None