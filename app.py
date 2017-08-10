import sys, os
from tornado.web import Application, StaticFileHandler
import tornado.httpserver
import tornado.ioloop
from tornado.options import define, options, parse_command_line
import tornado.web
from jinja2 import Environment, FileSystemLoader

# From SmartAPI website
src_path = os.path.split(os.path.split(os.path.abspath(__file__))[0])[0]
if src_path not in sys.path:
    sys.path.append(src_path)
print(src_path)

# Actual Path
actual_path = os.path.dirname(os.path.realpath(__file__))
print(actual_path)


STATIC_PATH = os.path.join(src_path, 'src/static')
print(STATIC_PATH)

TEMPLATE_PATH  = os.path.join(actual_path, 'templates')
print(TEMPLATE_PATH)

define("port", default=8888, help="run on the given port", type=int)
define("address", default="127.0.0.1", help="run on localhost")
define("debug", default=False, type=bool, help="run in debug mode")


tornado.options.parse_command_line()
if options.debug:
    import tornado.autoreload
    import logging
    logging.getLogger().setLevel(logging.DEBUG)
    options.address = '0.0.0.0'


# Docs: http://docs.python-guide.org/en/latest/scenarios/web/
# Load template file templates/site.html
templateLoader = FileSystemLoader( searchpath="templates/" )
templateEnv = Environment( loader=templateLoader, cache_size=0 )


TEMPLATE_FILE = "site.html"
template = templateEnv.get_template(TEMPLATE_FILE)
# List for famous movie rendering
movie_list = [[1,"The Hitchhiker's Guide to the Galaxy"],[2,"Back to future"],[3,"Matrix"]]
# template.render() returns a string which contains the rendered html
html_output = template.render(list=movie_list,
                        title="Here is my favorite movie list")

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        # self.write("Hello, world")
        self.write(html_output)
        template.render(list=movie_list,
                        title="Here is my favorite movie list")


# TEST
INDEX_FILE = "index.html"
index_template = templateEnv.get_template(INDEX_FILE)
index_output = index_template.render()


class TestHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(index_output)


# Registration Form
REG_FILE = "reg_form.html"
reg_template = templateEnv.get_template(REG_FILE)
reg_output = reg_template.render()

class RegistrationHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(reg_output)



# https://stackoverflow.com/questions/12031007/disable-static-file-caching-in-tornado
# class MyStaticFileHandler(tornado.web.StaticFileHandler):
#     def set_extra_headers(self, path):
#         # Disable cache
#         self.set_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')




APP_LIST = [
    (r"/", MainHandler),
    (r"/test", TestHandler),
    (r"/registration", RegistrationHandler)
]

settings = {
    "static_path": STATIC_PATH,
    "template_path": TEMPLATE_PATH,
    "compiled_template_cache": False
}


def main():
    application = tornado.web.Application(APP_LIST, **settings)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port, address=options.address)
    loop = tornado.ioloop.IOLoop.instance()
    if options.debug:
        tornado.autoreload.start(loop)
        logging.info('Server is running on "%s:%s"...' % (options.address, options.port))
    loop.start()


if __name__ == "__main__":
    main()

