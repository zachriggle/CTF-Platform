__author__ = "Collin Petty"
__copyright__ = "Carnegie Mellon University"
__license__ = "MIT"
__maintainer__ = ["Collin Petty", "Peter Chapman"]
__credits__ = ["David Brumely", "Collin Petty", "Peter Chapman", "Tyler Nighswander", "Garrett Barboza"]
__email__ = ["collin@cmu.edu", "peter@cmu.edu"]
__status__ = "Production"

from common import db
import common
import group

import bcrypt


def register_team(request):
    """Register a new team.

    Checks that an email address, team name, adviser name, affiliation, and password were sent from the browser.
    If any of these are missing a status:0 is returned with a message saying that all fields must be provided.
    Verifies that no teams exist with the specified name, if one exists a status:0 with a message is returned.
    If the 'joingroup' flag is empty or false and the passed 'group' is not empty we check to see if a group with that
    name exists in the database, if it does we return a status:2 and a message saying the the group exists, and give
    the user the option to join it.
    If no failure at this point the function hashes the password and inserts the data into a new db document
    in the teams collection.
    If the passed 'group' was empty we now return a status:1 with a successful registration message. If the 'joingroup'
    flag was set/true (and 'group' exists) we search for the group, if it does NOT exist we create it and add the new
    team as an owner and member.  If it does exist we add the team as a member of the group.
    If 'joingroup' is not set/false but 'group' exists then we create the new group and add the user as an owner/member,
    we already know that the group does not exist (would have been caught at the beginning).
    """
    email = request.form.get('email', '')
    teamname = request.form.get('teamname', '')
    adviser = request.form.get('name', '')
    affiliation = request.form.get('aff', '')
    pwd = request.form.get('password', '')
    gname = request.form.get('group', '').lower().strip('')
    joingroup = 'true' #request.form.get('joingroup', '')
    print {email, teamname, pwd}
    if '' in {email, teamname, pwd}:
        return {'success': 0, 'message': "Please fill in all of the required fields."}
    if db.teams.find({'teamname': teamname}).count() != 0:
        return {'success': 0, 'message': "That team name is already registered."}
    # if joingroup != 'true' and gname != '':
        # if db.groups.find({'name': gname}).count() != 0:
            # return {'success': 2, 'message': "The group name you have entered exists, would you like to join it?"}

    tid = common.token()
    db.teams.insert({'email': str(email),
                     'advisor': str(adviser),
                     'teamname': str(teamname),
                     'affiliation': str(affiliation),
                     'pwhash': bcrypt.hashpw(str(pwd), bcrypt.gensalt(8)),
                     'tid': tid})
    if gname == '':
        return {'success': 1, 'message': "Success! You have successfully registered."}

    if joingroup == 'true':
        if db.groups.find({'name': gname}).count() == 0:
            group.create_group(tid, gname)
        else:
            db.groups.update({'name': gname}, {'$push': {'members': tid}})
            return {'success': 1, 'message': 'Success! You have been added to the group!'}
    else:
        group.create_group(tid, gname)
        return {'success': 1, 'message': "Success! You are registered and have created your group."}


def update_password(tid, request):
    """Update account password.

    Gets the new password and the password entered into the 'confirm password' box and verifies that 1) The new pw is
    not empty and 2) the new pw and the conf pw are the same. We salt/hash the password and update the team object
    in mongo then return a status:1 with a success message.
    """
    pwd = request.form.get('pwd', '')
    conf = request.form.get('conf', '')
    if pwd == '':
        return {'success': 0, 'message': "The new password cannot be emtpy."}
    if pwd != conf:
        return {'success': 0, 'message': "The passwords do not match."}
    db.teams.update({'tid': tid}, {'$set': {'pwhash': bcrypt.hashpw(pwd, bcrypt.gensalt(8))}})
    return {'success': 1, 'message': "Success! Your password has been updated."}


def get_ssh_account(tid):
    """Get a webshell account.

    Searches the sshaccts collection for a document that has the current team's tid, if one is found the creds are
    returned. If no ssh account is associated with the user an account with no tid is selected and assigned to the
    current team. The credentials are then returned. If no unused accounts are found an error email is sent to the
    admin_emails list and an error is returned.
    """
    sshacct = db.sshaccts.find_one({'tid': tid})
    if sshacct is not None:
        return {'username': sshacct['user'], 'password': sshacct['password']}
    sshacct = db.sshaccts.find_one({'$or': [{'tid': ''}, {'tid': {'$exists': False}}]})
    if sshacct is not None:
        db.sshaccts.update({'_id': sshacct['_id']}, {'$set': {'tid': tid}})
        return {'username': sshacct['user'], 'password': sshacct['password']}
    else:
        common.log('No free SSH accounts were found in the database.')