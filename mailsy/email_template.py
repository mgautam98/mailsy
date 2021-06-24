from jinja2 import Environment, FileSystemLoader
import os


def get_templated(email):
    env = Environment(
        loader=FileSystemLoader("%s/templates/" % os.path.dirname(__file__))
    )
    template = env.get_template("email.html")
    output = template.render(email=email)

    return output


if __name__ == "__main__":
    email = {
        "name": "Gautam Mishra",
        "from": "gautam.mishra@example.com",
        "to": "gautam.mishra@gmail.com",
        "msg": "Hope you are doing will! \n It has been so long we didn't meet,\
            let's catch up tomorrow at Brew & Pub.",
    }

    print(get_templated(email))
