import sqlalchemy as sa
from rdfdatabank.model import init_model
from rdfdatabank.lib.auth_entry import add_user, add_user_groups
import ConfigParser
import sys, os, json
from rdfdatabank.lib.unicodeCSV import UnicodeReader, UnicodeWriter

class AddUser():
    def __init__(self):
        #Initialize sqlalchemy
        f = '/var/lib/databank/production.ini'
        if not os.path.exists(f):
            print "Config file not found"
            sys.exit()
        c = ConfigParser.ConfigParser()
        c.read(f)
        if not 'app:main' in c.sections():
            print "Section app:main not found in config file"
            sys.exit()

        engine = sa.create_engine(c.get('app:main', 'sqlalchemy.url'))
        init_model(engine)
        return

    def add_user(self, username, password, name=None, firstname=None, lastname=None, email=None, membership=[]):
        # groups = [(silo1, role1),(silo2, role2)]
        #add user
        user_details = {
        'username':u'%s'%username,
        'password':u"%s"%password
        }
        if name and name.strip():
            user_details['name'] = name.strip()
        if firstname and firstname.strip():
            user_details['firstname'] = firstname.strip()
        if lastname and lastname.strip():
            user_details['lastname'] = lastname.strip()
        if email and email.strip():
            user_details['email'] = email.strip()

        #print user_details
        #print membership
        add_user(user_details)
        if membership:
            #Add user membership
            add_user_groups(username, membership)
        return

    def addUsersFromCSV(self, filename, heading=True):
        #csvfile order
        csvfo = file(filename, 'r')
        ur = UnicodeReader(csvfo)
        heading=ur.next()

        logfo = file('/var/log/databank/addUserFromCSV.log', 'w')
        uw = UnicodeWriter(logfo)
        title = []
        title.extend(heading)
        title.append('result')

        try:
            ui = heading.index('username')
        except:
            return False

        uw.writerow(title)
        logfo.flush()

        try:
            pi = heading.index('password')
        except:
            return False

        try:
            nmi = heading.index('name')
        except:
            nmi = -1

        try:
            fni = heading.index('firstname')
        except:
            fni = -1

        try:
            lni = heading.index('lastname')
        except:
            lni = -1

        try:
            emi = heading.index('email')
        except:
            emi = -1

        try:
            gpi = heading.index('membership')
        except:
            gpi = -1

        data = ur.next()
        while data:
            if not data[ui] or not data[pi]:
                try:
                    data = ur.next()
                except:
                    data.append('False-No username or password')
                    uw.writerow(data)
                    logfo.flush()
                    data = None
                continue
            name= None
            firstname = None
            lastname = None
            email = None
            groups = []
            if nmi > -1 and data[nmi]:
                name = data[nmi]
            if fni > -1 and data[fni]:
                firstname = data[fni]
            if lni > -1 and data[lni]:
                lastname = data[lni]
            if emi > -1 and data[emi]:
                email = data[emi]
            if gpi > -1 and data[gpi]:
                data[gpi] = data[gpi].replace("'", '"')
                membership = json.loads(data[gpi])
                if type(membership).__name__ == 'list':
                   for member in membership:
                        if not type(member).__name__ == 'list' and len(member) == 2:
                             continue
                        groups.append(member)

            ans = self.add_user(data[ui], data[pi], name=name, firstname=firstname, lastname=lastname, email=email, membership=groups)
            data.append(str(ans))
            uw.writerow(data)
            logfo.flush()
            
            try:
                data = ur.next()
            except:
                data = None
        csvfo.close()
        logfo.close()

