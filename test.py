import web
import re
s = '121.23 232.21 23.12 23.21 21.34 21 553 232 52 151 312 232 232 125 5635.21 '
m = re.findall(r'\d+\.?\d*',s)

num = [float(i) for i in m]
id = 0
item = []
print num
for v in num:
    print(v)

class Index(object):
 def GET(self):
  pass

#s = str(theValue)
#m = re.findall(r'\d+\.?\d*',s)
#list = [float(i) for i in m]
#id =0

for v in list:
    id = id +1

    if id == 3:
        pass
    #MySQLConn.get().db.insert(tableName,refTime = refTime,theValue = theValue, freq = formFreq)
    else:
        #return titled_render().error()
        pass
    try:
        for v in list:
            id = id +1
            if id == 3:
                pass

                        #MySQLConn.get().db.insert(tableName, refTime=refTime, theValue=theValue,freq = formFreq)
            else:
                        pass
                        #return titled_render().error(error = 'Lost some data')

    except Exception,e:

                            pass
                        #return titled_render().error(error = e.message)

#coding=utf-8

import requests
def getStatusCode(url):
   r = requests.get(url, allow_redirects = False)
   return r.status_code
print getStatusCode('http://www.baidu.com/')
