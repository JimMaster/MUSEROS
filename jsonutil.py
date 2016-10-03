import json
import web
class JsonUtil(object):

    @classmethod
    def successMsgJson(cls,str):
        web.header('Content-Type','application/text')

        return "{\"status\":success"",\"result\":\""+str+"\"}"

    @classmethod
    def errorMsgJson(cls,str):
        web.header('Content-Type','application/text')
        return "{\"status\":failed,\"result\":\""+str+"\"}"

    @classmethod
    def successObjJson(self,obj):
        header = web.header('Content-Type','application/json')
        return "{\"status\":success:,\"result\":"+json.dumps(obj)+"}"


#,\"object2\":"+json.dumps(obj2)+"}"
#return "{\"status\":success:"+header+",\"object\":"+json.dumps(obj1)+"}"
#172.31.254.25:3306,muser,muser,muser