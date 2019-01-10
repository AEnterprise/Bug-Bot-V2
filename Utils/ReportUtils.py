# Validators: return error message on fail, empty string on pass
# probably a better way to do this, but this works pretty good for now

def no_empty(input):
    return "Empty values are not allowed" if len(input) is 0 else ""


def no_glitch(input):
    return "Pls do not use the term 'glitch'" if "glitch" in input else ""


def valid_user(input):
    try:
        int(input)
    except ValueError:
        return "Not a user ID"
    else:
        # TODO: validate user is in server or not banned
        return ""


fields = dict(title=[no_empty, no_glitch],
              steps=[no_empty],
              expected=[no_empty, no_glitch],
              actual=[no_empty, no_glitch],
              client_info=[no_empty],
              device_info=[no_empty],
              platform=[no_empty],
              user_id=[valid_user]
              )


def validate(data):
    problems = []
    for name, checkers in fields.items():
        if name not in data:
            problems.append(dict(field=name, description="This is a required field"))
        else:
            for c in checkers:
                description = c(data[name])
                if description != "":
                    problems.append(dict(field=name, description=description))
    return problems
