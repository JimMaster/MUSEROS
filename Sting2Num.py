import re
from jsonutil import JsonUtil
import string
from api import *
import web
from browser import *
s = '121.23 232.21 23.12 23.21 21.34 21 553 232 52 151 312 232 232 125 5635.21 '
web.config.debug =False

web.config.debug =False

if sys.platform == "win32":#for developer
    WebStaticFullPath = "G:\\work\\MUSEROS\\src\\python\\opencluster\\ui\\res" #for developer
    WebMuserStaticFullPath = "G:\\work\\MUSEROS\\src\\python\\muserconf\\res" #for developer
    SatelliteFileRoot = "G:\\astrodata"
    SatelliteFileOutputRoot = "G:\\astrodata"



render = web.template.render('templates/')

urls = (
     "/","Index",
)

class Index(object):
    def GET(self):
        req =web.input()
        #s = MySQLConn.get().db.query('select*from t_test'+'t_test'+theValue)
        m = re.findall(r'\d+\.?\d*',s)
        num = [float(i) for i in m]
        id = 0
        item = []
        for i in num:
            id = id +1
            item[id] = i



    def POST (self):
        req = web.input()
        s = req.values

        #MySQLConn.get().db.insert('t_test',keyName = id ,theValue = s)
        web.seeother("/?string="+1)

    """
    def String2Num(self):
        id =0
        item={}
        for i in self.num:

            id = id+ 1
            item[id] = i


            MySQLConn.get().db.insert('t_test', keyName = id, theValue= i)


        try:
            if (id==13):
                return web.template.render('string')
            elif(id<13):
                return JsonUtil.errorMsgJson('lost some data, please submit again!')
            else:
                return JsonUtil.errorMsgJson('need more data, please submit again!')
        except Exception:
            pass
        """

if __name__ == "__main__" :
    app = web.application(urls,globals())
    app.run()



