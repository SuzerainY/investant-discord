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