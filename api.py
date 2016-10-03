import web
import redis
from jsonutil import JsonUtil
#from ocscripts.conf import MUSERConf
#from ocscripts.kafkaUtils import KafkaUtils
from redisClient import *
import kafkaUtils
import cPickle
from browser import *
import json
try :
    from kafka import SimpleProducer, KafkaClient, KeyedProducer,SimpleClient
except:
    raise Exception("kafka-python is not installed")

class KafkaUtils(object):

    def __init__(self,addr):
        self.kafka_client = SimpleClient(addr)

    def produceTasks(self,tasks):
        producer = KeyedProducer(self.kafka_client)
        for task in tasks:
            producer.send_messages(task.warehouse, task.jobName, cPickle.dumps(task))

    def close(self):
        if self.kafka_client:
            self.kafka_client.close()

#kafkaUtil = KafkaUtils(MUSERConf.getKafka())
apiUrls = [
            "/res/(.*)", "StaticRes",
            "/muserres/(.*)", "MuserStaticRes",
            "/api", "IndexApi",
            "/antenna/api", "AntennaListApi",
            "/antennaOp/(.*)", "AntennaOperationApi",
            "/calibration/(.*)", "CalibrationListApi",
            "/calibrationOp/(.*)","CalibrationOperationApi",
            "/config/(.*)", "ConfigListApi",
            "/configInfo/api","ConfigInfoApi",
            "/configOp/(.*)","ConfigOperationApi",

            "/integration/(.*)", "IntegrationListApi",
            "/integrationOp/(.*)","IntegrationOperationApi",
            "/integrationTasks/(.*)","IntegrationTasksApi",
            "/integrationTaskOp/(.*)","IntegrationTaskOperationApi",
            "/integrationResults/(.*)","IntegrationResultsApi",
            "/imaging/(.*)", "ImagingListApi",
            "/download/(.*)", "DownloadApi",
            "/imagingOp/(.*)","ImagingOperationApi",
            "/weather/(.*)", "WeatherListApi",
            "/weatherOp/(.*)","WeatherOperationApi",
            "/rawfile/(.*)","RawFileApi",

]
def operator_status(func):
    '''''get operatoration status
    '''
    def gen_status(*args, **kwargs):
        error, result = None, None
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            error = str(e)
        return {'result': result, 'error':  error}
    return gen_status

class RedisPool(object):
    _instance = None
    def __init__(self):
        redisStr = MUSERConf.getRedis()
        redisIpAndPort = redisStr.split(":")
        self.pool = redis.ConnectionPool(host=redisIpAndPort[0], port=int(redisIpAndPort[1]), db=0)
    @staticmethod
    def get():
        if RedisPool._instance is None:
            RedisPool._instance = RedisPool().pool
        return RedisPool._instance

class MySQLConn(object):
    _instance = None
    def __init__(self):
        mysqlStr = MUSERConf.getMySQL()
        mysqlUrls = mysqlStr.split(",")
        mysqlIpAndPort = mysqlUrls[0].split(":")
        self.db = web.database(dbn='mysql', db=mysqlUrls[1], user=mysqlUrls[2],passwd=mysqlUrls[3],host=mysqlIpAndPort[0],port=int(mysqlIpAndPort[1]))
    @staticmethod
    def get():
        if MySQLConn._instance is None:
            MySQLConn._instance = MySQLConn()
        return MySQLConn._instance

#web.config.debug = True

class Hello(object):
    def GET(self):
        return "hello "
    def PUT(self):
        return "hello "

class IndexApi(object):
    def GET(self):
        try :
            items = {}
            mysqlState = ""

            try:
                mysqlState = MySQLConn.get().db.query("select version() as v")[0]
            except Exception, e:
                mysqlState = {"v":""}

            redisState = RedisCache().redis_version()
            redis_dump_ver = RedisCache().get_data("dumpver")

            rawfileCount = MySQLConn.get().db.query("select count(*) as d from t_raw_file")[0]
            rawfileLastTime = MySQLConn.get().db.query("select max(startTime) as d from t_raw_file")[0]

            integrations = MySQLConn.get().db.query("select count(*) as d,status from t_integration group by status")
            imagings = MySQLConn.get().db.query("select count(*) as d,status from t_imaging group by status")

            weather = MySQLConn.get().db.query("select theValue as d,refTime from p_weather order by  refTime DESC limit 1")[0]
            position1 = MySQLConn.get().db.query("select theValue as d from p_antenna_position where freq=1 order by  refTime DESC limit 1")[0]
            position2 = MySQLConn.get().db.query("select theValue as d from p_antenna_position where freq=2 order by  refTime DESC limit 1")[0]

            flag1 = MySQLConn.get().db.query("select theValue as d from p_antenna_flag where freq=1 order by  refTime DESC limit 1")[0]
            flag2 = MySQLConn.get().db.query("select theValue as d from p_antenna_flag where freq=2 order by  refTime DESC limit 1")[0]

            delay1 = MySQLConn.get().db.query("select theValue as d from p_antenna_delay where freq=1 order by  refTime DESC limit 1")[0]
            delay2 = MySQLConn.get().db.query("select theValue as d from p_antenna_delay where freq=2 order by  refTime DESC limit 1")[0]

            items["rawfileCount"] = rawfileCount.d
            items["rawfileLastTime"] = rawfileLastTime.d

            items["position"] = (position1.d,position2.d)
            items["delay"] = (delay1.d,delay2.d)
            items["flag"] = (flag1.d,flag2.d)
            items["weather"] = weather.d
            items["weatherTime"] = str(weather.refTime)

            items["integration"] = {"tasks":0,"running":0,"error":0,"finished":0}
            items["imaging"] = {"tasks":0,"running":0,"error":0,"finished":0}

            for item in integrations:
                items["integration"]["tasks"] += int(item.d)
                if item.status == 2:
                    items["integration"]["running"] = int(item.d)
                elif item.status == 3:
                    items["integration"]["finished"] = int(item.d)
                elif item.status == 4:
                    items["integration"]["error"] = int(item.d)

            for item in imagings:
                items["imaging"]["tasks"] += int(item.d)
                if item.status == 2:
                    items["imaging"]["running"] = int(item.d)

                elif item.status == 3:
                    items["imaging"]["finished"] = int(item.d)
                elif item.status == 4:
                    items["imaging"]["error"] = int(item.d)
            web.header('Content-Type','application/json')
            return JsonUtil.successObjJson(items)
        except Exception, e:
            return JsonUtil.errorMsgJson("Not Found 404")

class AntennaListApi(object):
    def GET(self):
        try :
            req = web.input()
            key = str(req.key)
            tableName = ""
            if key == "Position" :
                tableName = "p_antenna_position"
            elif key == "Flag" :
                tableName = "p_antenna_flag"
            elif key == "Delay" :
                tableName = "p_antenna_delay"
            elif key == "Status" :
                tableName = "p_instrument_status"
            else:
                raise Exception("invalid key")
            """
            if req.has_key("action") :
                id = req.id
                items = MySQLConn.get().db.query("select * from "+tableName+" where id=" + id)
                obj = items[0]
                item = {}
                item["refTime"] = str(obj.refTime)
                item["freq"] = str(obj.freq)
                item["theValue"] = str(obj.theValue)
                item["id"] = str(obj.id)
                return JsonUtil.successObjJson(item)
            """
            if req.has_key("beginTime") :
                beginTime = str(req.beginTime)
            else:
                beginTime = ""
            if req.has_key("endTime") :
                endTime = str(req.endTime)
            else :
                endTime = ""

            if req.has_key("freq") :
                freq = str(req.freq)
            else :
                freq = "0"

            if not beginTime :
                beginTime = time.strftime("%Y-%m-%d 00:00:00",time.localtime(time.time()-25920000))
            if not endTime :
                endTime = time.strftime("%Y-%m-%d 23:59:59",time.localtime(time.time()))

            datesets = MySQLConn.get().db.query("select * from "+tableName+" where TO_DAYS(refTime)>=TO_DAYS('" + beginTime +  "') and TO_DAYS(refTime)<=TO_DAYS('" + endTime +  "') and ("+freq+"=0 or freq="+freq+")")
            items = []
            for v in datesets:

                item = {}
                item["freq"] = str(v.freq)
                item["theValue"] = str(v.theValue or "")
                #item["beginTime"] = str(v.beginTime or "")
                #item["endTime"] = str(v.endTime)
                items.append(item)
            web.header('Content-Type','application/json')
            return JsonUtil.successObjJson(items)
        except Exception, e:
            return JsonUtil.errorMsgJson(str(e.message))

class AntennaOperationApi(object):
    def GET(self):
        self.operation()
    def POST(self):
        self.operation()
    def operation(self):
        try :
            req = web.input()
            key = str(req.key)
            action = str(req.action)

            tableName = ""
            if key == "Position" :
                tableName = "p_antenna_position"
            elif key == "Flag" :
                tableName = "p_antenna_flag"
            elif key == "Delay" :
                tableName = "p_antenna_delay"
            elif key == "Status" :
                tableName = "p_instrument_status"
            else:
                raise Exception("invalid key")

            if req.has_key("beginTime") :
                beginTime = str(req.beginTime)
            else:
                beginTime = ""
            if req.has_key("endTime") :
                endTime = str(req.endTime)
            else :
                endTime = ""
            if not beginTime :
                beginTime = time.strftime("%Y-%m-%d",time.localtime(time.time())) + " 00:00:00"
            if not endTime :
                endTime = time.strftime("%Y-%m-%d",time.localtime(time.time())) + " 23:59:59"

            if req.has_key("freq") :
                freq = str(req.freq)
            else :
                freq = "0"

            if action == "remove" :
                id = str(req.id)
                MySQLConn.get().db.delete(tableName, where="id=" + id)
                return JsonUtil.successMsgJson("data delete")

            if action == "add" :
                refTime = req.refTime
                theValue = req.theValue
                formFreq = req.formFreq
                sequence_id = MySQLConn.get().db.insert(tableName, refTime=refTime, theValue=theValue,freq = formFreq)
                items ={}
                items['refTime'] = refTime
                items['theValue'] = theValue
                items['formFreq'] = formFreq
                return JsonUtil.successObjJson(items)


            if action == "edit" :
                id = str(req.id)
                refTime = req.refTime
                theValue = req.theValue
                formFreq = req.formFreq
                MySQLConn.get().db.update(tableName,where="id="+id,  refTime=refTime, theValue=theValue,freq = formFreq)
                items ={}
                items['refTime'] = refTime
                items['theValue'] = theValue
                items['formFreq'] = formFreq
                return JsonUtil.successObjJson(items)

            web.seeother("antenna?freq="+freq+"&key=" + key + "&beginTime="+beginTime + "&endTime="+ endTime)
        except Exception, e:
            return JsonUtil.errorMsgJson(str(e.message))

class CalibrationListApi(object):
    def GET(self):
        try :
            req = web.input()
            if req.has_key("action") :
                id = req.id
                items = MySQLConn.get().db.query("select * from t_calibration where id=" + id)
                obj = items[0]
                item = {}
                item["ctime"] = str(obj.ctime)
                item["priority"] = obj.priority
                item["offset"] = int(obj.offset)
                item["status"] = obj.status
                item["freq"] = obj.freq
                item["description"] = str(obj.description or "")
                jsonStr = str(item)
                web.header('Content-Type','application/json')
                return jsonStr.replace("'","\"")

            if req.has_key("beginTime") :
                beginTime = str(req.beginTime)
            else:
                beginTime = ""
            if req.has_key("endTime") :
                endTime = str(req.endTime)
            else :
                endTime = ""

            if not beginTime :
                beginTime = time.strftime("%Y-%m-%d",time.localtime(time.time()))
            if not endTime :
                endTime = time.strftime("%Y-%m-%d",time.localtime(time.time()))

            v_beginTime = time.mktime(time.strptime(beginTime,"%Y-%m-%d"))
            v_endTime = time.mktime(time.strptime(endTime,"%Y-%m-%d"))


            if not req.has_key("key") :
                raise Exception("lack key!!!")
            key = req.key

            datasets = MySQLConn.get().db.query("select * from t_calibration where TO_DAYS(ctime)>=TO_DAYS('" + beginTime +  "') and TO_DAYS(ctime)<=TO_DAYS('" + endTime +  "') and freq=" + str(key))
            web.header('Content-Type','application/json')
            for v in datasets:
                pass

            return JsonUtil.successObjJson(items)
        except Exception, e:
            return JsonUtil.errorMsgJson(str(e.message))

class ConfigOperationApi(object):
    def GET(self):
        self.operation()
    def POST(self):
        self.operation()
    def operation(self):
        try :
            req = web.input()

            key = str(req.key)
            id = str(req.id)
            action = str(req.action)

            if action == "remove" :
                MySQLConn.get().db.delete('t_config', where="id=" + id)
                return JsonUtil.successMsgJson("delete success")

            if action == "add" :
                keyName = req.keyName
                createTime = req.createTime
                theValue = req.theValue
                sequence_id = MySQLConn.get().db.insert('t_config', keyName=keyName,theValue=theValue,createTime=createTime)
                item = {}
                item["keyName"] = keyName
                item["theValue"] = theValue
                item["createTime"] = createTime
                web.header('Content-Type','application/json')
                return JsonUtil.successObjJson(item)

            if action == "edit" :
                keyName = req.keyName
                theValue = req.theValue
                createTime = req.createTime
                MySQLConn.get().db.update('t_config',where="id="+id, keyName=keyName,theValue=theValue,createTime=createTime)
                item = {}
                item["keyName"] = keyName
                item["theValue"] = theValue
                item["createTime"] = createTime
                web.header('Content-Type','application/json')
                return JsonUtil.successObjJson(item)


            web.seeother("config?key=" + key)
        except Exception, e:
            return JsonUtil.errorMsgJson(str(e.message))

class ConfigInfoApi(object):
    def GET(self):
        try :
            req = web.input()
            id = req.id
            datasets = MySQLConn.get().db.query("select * from t_config where id=" + id)
            items = []
            for it in datasets:
                item = {}
                item["id"] = it.id
                item["keyName"] = str(it.keyName)
                item["createTime"] = str(it.createTime)
                #item["freq"] = it.freq
                item["theValue"] = str(it.theValue)
                #item["description"] = str(it.description)
                items.append(item)



            web.header('Content-Type','application/json')
            return JsonUtil.successMsgJson(items)
        except Exception, e:
            return JsonUtil.errorMsgJson(str(e.message))
"""
class ConfigListApi(object):
    def GET(self):
        try :
            req = web.input()
            key = ""
            if req.has_key("key"):
                key = req.key
            datasets = MySQLConn.get().db.query("select * from t_config where keyName like '%" + key +  "%'")
            items = []
            for it in datasets:
                item = {}
                item["id"] = it.id
                item["keyName"] = str(it.keyName)
                item["createTime"] = str(it.createTime)
                item["freq"] = it.freq
                item["theValue"] = str(it.theValue)
                item["description"] = str(it.description)
                items.append(item)

            return JsonUtil.successObjJson(items)
        except Exception, e:
            return JsonUtil.errorMsgJson(str(e.message))

    def PUT(self):
        pass

    def DELETE(self):
        pass
        keyNames = MySQLConn.get().db.query("select * from t_config_key")
"""
class ConfigListApi(object):
    def GET(self):
        try :
            req = web.input()
            key = req.key
            datasets = MySQLConn.get().db.query("select * from t_config where keyName like '%" + key +  "%'")
            items = []
            for it in datasets:
                item = {}
                item["id"] = it.id
                item["keyName"] = str(it.keyName)
                item["createTime"] = str(it.createTime)
                #item["freq"] = it.freq
                item["theValue"] = str(it.theValue)
                #item["description"] = str(it.description)
                items.append(item)
            web.header('Content-Type','application/json')

            return JsonUtil.successObjJson(items)


        except Exception, e:
            return titled_render().error(error=e.message)
class IntegrationResultsApi(object):
    def GET(self):
        try :
            req = web.input()
            action = str(req.action)
            id = str(req.id)

            if action == "results" :
                items = MySQLConn.get().db.query("select * from t_integration_task where status=2 and int_id=" + id)
                results = []
                for it in items :
                    results.extend(str(it.results).split(","))

                integrations = MySQLConn.get().db.query("select * from t_integration where id=" + id)
                obj = integrations[0]

                return titled_render().integrationResults(items = results,integration = obj)

            if action=="download":
                web.header('Content-Type','application/octet-stream')
                web.header('Content-disposition', 'attachment; filename=%s' % id.split("/")[-1])
                try :
                    f = open(id,"rb")
                    return f.read()
                finally:
                    if f :
                        f.close()
            web.seeother("integrationTasks?id="+id)
            return JsonUtil.successMsgJson("Integration Successfully")


        except Exception, e:
            traceback.print_exc()
            return JsonUtil.errorMsgJson(str(e.message))

class DownloadApi(object):
    def GET(self):
        try :
            req = web.input()
            fileName = str(req.file)

            web.header('Content-Type','application/octet-stream')
            web.header('Content-disposition', 'attachment; filename=%s' % fileName.split("/")[-1])
            f = None
            try :
                f = open(fileName,"rb")
                return f.read()
            finally:
                if f :
                    f.close()
                return JsonUtil.successMsgJson("finished")

        except Exception, e:
            traceback.print_exc()
            return titled_render().error(error=e.message)

class IntegrationTasksApi(object):
    def GET(self):
        try :
            req = web.input()
            action = str(req.action)
            id = str(req.id)
            if action == "detail":
                integration = {}
                integrations = MySQLConn.get().db.query("select * from t_integration where id=" + id)
                obj = integrations[0]
                item = {}
                item["beginTime"] = str(obj.beginTime)
                item["endTime"] = str(obj.endTime)
                item["status"] = obj.status
                item["freq"] = obj.freq
                item["seconds"] = obj.seconds
                item["format"] = str(obj.format)
                item["job_id"] = str(obj.job_id)
                item["is_specified_file"] = obj.is_specified_file
                item["specified_file"] =str(obj.specified_file or "")
                item["big_file"] = str(obj.big_file or "")
                item["description"] = str(obj.description or "")
                item["task_num"] = obj.task_num
                item["results"] = str(obj.results or "")
                item["task_percent"] = 0
                item["task_remain"] = 0


                items = MySQLConn.get().db.query("select count(*) as d,repeat_num from t_integration_task where (status=2 or status=3) and int_id="+id)
                if len(items)>0 and item["task_num"] > 0:
                    tasksNum = items[0]
                    item["task_percent"] = int((float(tasksNum.d or 0)/item["task_num"])*100)
                    item["task_remain"] = int(item["seconds"]*60*float(tasksNum.repeat_num or 0)*(item["task_num"]-float(tasksNum.d or 0))) + 60

                    print tasksNum
                    print item["task_percent"]

                tasks = MySQLConn.get().db.query("select * from t_integration_task where int_id="+id)
                return JsonUtil.successObjJson(item)
            web.seeother("integrationTasks?id="+id)
        except Exception, e:
            traceback.print_stack()
            return JsonUtil.errorMsgJson(str(e.message))

class IntegrationTaskOperationApi(object):
    def GET(self):
        self.operation()
    def POST(self):
        self.operation()
    def operation(self):
        try :
            req = web.input()
            id = str(req.id)
            action = str(req.action)
            int_id = "0"
            if action == "reset" :
                MySQLConn.get().db.update('t_integration_task',where="task_id='" + id + "'", status=1)
                items = MySQLConn.get().db.query("select * from t_integration_task where task_id='" + id + "'")

                if len(items)>0 :
                    obj = items[0]
                    int_id = str(obj.int_id)

                    task_data = ObjValue()
                    task_data.setObj("timeStr",str(obj.timeStr))
                    task_data.setObj("freq",obj.freq)
                    task_data.setObj("integralNumber",obj.int_number)
                    task_data.setObj("repeat",obj.repeat_num)

                    task = Task(id=id,data=task_data,\
                                workerClass="integrationWorker.IntegrationWorker",workDir = os.path.dirname(os.path.abspath(__file__)) + "/../ocscripts",priority=3,\
                                resources={"cpus":1,"mem":500,"gpus":0},\
                                warehouse="OpenCluster3",\
                                jobName=str(obj.job_id))

                    kafkaUtil.produceTasks([task])

            #web.seeother("integrationTasks?action=detail&id=" + int_id)
            return JsonUtil.successMsgJson("finished")
        except Exception, e:
            traceback.print_stack()
            return JsonUtil.errorMsgJson("failed")

class IntegrationOperationApi(object):
    def GET(self):
        self.operation()
    def POST(self):
        self.operation()
    def operation(self):
        try :
            req = web.input()
            id = str(req.id)
            action = str(req.action)
            beginTime = req.beginTime
            endTime = req.endTime
            if action == "remove" :
                MySQLConn.get().db.delete('t_integration', where="id=" + id)
                return JsonUtil.successMsgJson("delete finished")

            if action == "detail" :
                items = []
                datasets = MySQLConn.get().db.query("select * from t_integration_task where int_id=" + id)
                for v in datasets:
                    item = {}
                    item['beginTime'] = v.beginTime
                    item['endTime'] = v.endTime
                return JsonUtil.successObjJson(items)

            if action == "add" :
                items = {}
                items['fBeginTime'] = req.fBeginTime
                items['fEndTime'] = req.fEndTime
                items['seconds'] = req.seconds
                items['freq'] = req.freq
                items['description'] = req.description
                items['format'] = req.format
                is_specified_file = req.is_specified_file
                specified_file = req.specified_file

                sequence_id = MySQLConn.get().db.insert('t_integration', status=0, beginTime=items['fBeginTime'], endTime=items['fEndTime'], \
                                        seconds=items['seconds'], freq=items['freq'], format=items['format'], job_id=time.strftime("%Y%m%d%H%M%S",time.localtime(time.time())),\
                                        is_specified_file=is_specified_file, specified_file=specified_file, \
                                        createTime = time.strftime("%Y-%m-%d H%:M:%S",time.localtime(time.time())),\
                                        description=['description'])
                return JsonUtil.successObjJson(items)

            if action == "edit" :
                items = {}
                items['fBeginTime'] = req.fBeginTime
                items['fEndTime'] = req.fEndTime
                items['seconds'] = req.seconds
                items['freq'] = req.freq
                items['description'] = req.description
                items['format'] = req.format
                is_specified_file = req.is_specified_file
                specified_file = req.specified_file

                MySQLConn.get().db.update('t_integration',where="id="+id,  beginTime=items['fBeginTime'], endTime=items['fEndTime'], \
                                        seconds=items['seconds'], freq=items['freq'], format=items['format'], \
                                        is_specified_file=is_specified_file, specified_file=specified_file, \
                                        description=['description'])
                return JsonUtil.successObjJson(items)
            if action == "begin" :
                MySQLConn.get().db.update('t_integration',where="id="+id, status=1)


            web.seeother("integration?beginTime="+beginTime + "&endTime="+ endTime)
        except Exception, e:
            return JsonUtil.errorMsgJson(str(e.message))

class IntegrationListApi(object):
    def GET(self):
        try :
            req = web.input()
            if req.has_key("action") :
                id = req.id
                items = MySQLConn.get().db.query("select * from t_integration where id=" + id)
                obj = items[0]
                item = {}
                item["beginTime"] = str(obj.beginTime)
                item["endTime"] = str(obj.endTime)
                item["status"] = obj.status
                item["freq"] = obj.freq
                item["seconds"] = obj.seconds
                item["format"] = str(obj.format)
                item["is_specified_file"] = obj.is_specified_file
                item["specified_file"] =str(obj.specified_file or "")
                item["big_file"] = str(obj.big_file or "")
                item["description"] = str(obj.description or "")
                jsonStr = str(item)
                return JsonUtil.successObjJson(item)


            if req.has_key("beginTime") :
                beginTime = str(req.beginTime)
            else:
                beginTime = ""
            if req.has_key("endTime") :
                endTime = str(req.endTime)
            else :
                endTime = ""

            if not beginTime :
                beginTime = time.strftime("%Y-%m-%d 00:00:00",time.localtime(time.time()-2592000))
            if not endTime :
                endTime = time.strftime("%Y-%m-%d 23:59:59",time.localtime(time.time()))

            items = MySQLConn.get().db.query("select * from t_integration where TO_DAYS(createTime)>=TO_DAYS('" + beginTime +  "') and TO_DAYS(createTime)<=TO_DAYS('" + endTime +  "')")
            return JsonUtil.successObjJson(items)
        except Exception, e:
            return JsonUtil.errorMsgJson(str(e.message))

#--------------------------Weather---------------begin-----------------------------
class WeatherOperationApi(object):
    def GET(self):
        self.operation()
    def POST(self):
        self.operation()
    def operation(self):
        try :
            req = web.input()

            action = str(req.action)
            beginTime = req.beginTime
            endTime = req.endTime

            if action == "remove" :
                id = str(req.id)
                MySQLConn.get().db.delete('p_weather', where="id=" + id)
                return JsonUtil.successMsgJson("delete finished")

            if action == "add" :
                refTime = req.refTime
                theValue = req.theValue
                items ={}
                items['refTime'] = refTime
                items['theValue'] = theValue
                sequence_id = MySQLConn.get().db.insert('p_weather', refTime=refTime, theValue=theValue)
                return JsonUtil.successObjJson(items)

            if action == "edit" :
                id = str(req.id)
                refTime = req.refTime
                theValue = req.theValue
                items ={}
                items['refTime'] = refTime
                items['theValue'] = theValue
                MySQLConn.get().db.update('p_weather',where="id="+id,  refTime=refTime, theValue=theValue)
                return JsonUtil.successObjJson(items)

            web.seeother("weather?beginTime="+beginTime + "&endTime="+ endTime)
        except Exception, e:
            return JsonUtil.errorMsgJson(str(e.message))

class WeatherListApi(object):
    def GET(self):
        try :
            req = web.input()
            if req.has_key("action") :
                id = req.id
                items = MySQLConn.get().db.query("select * from p_weather where id=" + id)
                obj = items[0]
                item = {}
                item["refTime"] = str(obj.refTime)
                item["theValue"] = str(obj.theValue)
                item["id"] = str(obj.id)
                return JsonUtil.successObjJson(item)

            if req.has_key("beginTime") :
                beginTime = str(req.beginTime)
            else:
                beginTime = ""
            if req.has_key("endTime") :
                endTime = str(req.endTime)
            else :
                endTime = ""

            if not beginTime :
                beginTime = time.strftime("%Y-%m-%d 00:00:00",time.localtime(time.time()-2592000))
            if not endTime :
                endTime = time.strftime("%Y-%m-%d 23:59:59",time.localtime(time.time()))

            datasets = MySQLConn.get().db.query("select * from p_weather where TO_DAYS(refTime)>=TO_DAYS('" + beginTime +  "') and TO_DAYS(refTime)<=TO_DAYS('" + endTime +  "')")
            items = []
            for it in datasets:
                item = {}
                item["id"] = it.id
                item["keyName"] = str(it.keyName)
                item["createTime"] = str(it.createTime)
                #item["freq"] = it.freq
                item["theValue"] = str(it.theValue)
                #item["description"] = str(it.description)
                items.append(item)
            return JsonUtil.successObjJson(items)
        except Exception, e:
            return JsonUtil.errorMsgJson(str(e.message))

#--------------------------Weather---------------end-----------------------------

#--------------------------imaging---------------begin---------------------------

class ImagingOperation(object):
    def GET(self):
        self.operation()
    def POST(self):
        self.operation()
    def operation(self):
        try :
            req = web.input()
            id = str(req.id)
            action = str(req.action)
            beginTime = req.beginTime
            endTime = req.endTime
            if action == "remove" :
                MySQLConn.get().db.delete('t_imaging', where="id=" + id)
                return JsonUtil.successMsgJson("delete finished")

            if action == "add" :
                fBeginTime = req.fBeginTime
                fEndTime = req.fEndTime
                seconds = req.seconds
                freq = req.freq
                description = req.description
                format = req.format
                is_specified_file = req.is_specified_file
                specified_file = req.specified_file
                gen_result = req.gen_result
                with_axis = req.with_axis

                sequence_id = MySQLConn.get().db.insert('t_imaging', status=0, beginTime=fBeginTime, endTime=fEndTime, \
                                        seconds=seconds, freq=freq, format=format, job_id=time.strftime("%Y%m%d%H%M%S",time.localtime(time.time())),\
                                        is_specified_file=is_specified_file, specified_file=specified_file, \
                                        gen_result=gen_result, with_axis=with_axis, \
                                        createTime = time.strftime("%Y-%m-%d H%:M:%S",time.localtime(time.time())),\
                                        description=description)
                return JsonUtil.successObjJson(sequence_id)

            if action == "edit" :
                fBeginTime = req.fBeginTime
                fEndTime = req.fEndTime
                seconds = req.seconds
                freq = req.freq
                description = req.description
                format = req.format
                is_specified_file = req.is_specified_file
                specified_file = req.specified_file
                gen_result = req.gen_result
                with_axis = req.with_axis
                sequence_id = MySQLConn.get().db.update('t_imaging',where="id="+id, beginTime=fBeginTime,endTime=fEndTime,seconds=seconds,freq=freq,format=format, \
                                        is_specified_file=is_specified_file, specified_file=specified_file, \
                                    gen_result=gen_result, with_axis=with_axis, \
                                    description=description)
                return JsonUtil.successObjJson(sequence_id)

            if action == "begin" :
                sequence_id = MySQLConn.get().db.update('t_imaging',where="id="+id, status=1)
                return JsonUtil.successObjJson(sequence_id)


            web.seeother("imaging?beginTime="+beginTime + "&endTime="+ endTime)
        except Exception, e:
            return JsonUtil.errorMsgJson(str(e.message))

class ImagingList(object):
    def GET(self):
        try :
            req = web.input()
            if req.has_key("action") :
                id = req.id
                items = MySQLConn.get().db.query("select * from t_imaging where id=" + id)
                obj = items[0]
                item = {}
                item["beginTime"] = str(obj.beginTime)
                item["endTime"] = str(obj.endTime)
                item["status"] = obj.status
                item["freq"] = obj.freq
                item["seconds"] = obj.seconds
                item["format"] = str(obj.format)
                item["is_specified_file"] = obj.is_specified_file
                item["specified_file"] =str(obj.specified_file or "")
                item["big_file"] = str(obj.big_file or "")
                item["description"] = str(obj.description or "")
                item["gen_result"] = str(obj.gen_result or "")
                item["with_axis"] = obj.with_axis
                jsonStr = str(item)
                return JsonUtil.successObjJson(item)


            if req.has_key("beginTime") :
                beginTime = str(req.beginTime)
            else:
                beginTime = ""
            if req.has_key("endTime") :
                endTime = str(req.endTime)
            else :
                endTime = ""

            if not beginTime :
                beginTime = time.strftime("%Y-%m-%d 00:00:00",time.localtime(time.time()-2592000))
            if not endTime :
                endTime = time.strftime("%Y-%m-%d 23:59:59",time.localtime(time.time()))

            items = MySQLConn.get().db.query("select * from t_imaging where TO_DAYS(createTime)>=TO_DAYS('" + beginTime +  "') and TO_DAYS(createTime)<=TO_DAYS('" + endTime +  "')")
            return JsonUtil.successObjJson(items)
        except Exception, e:
            return JsonUtil.errorMsgJson(str(e.message))

#--------------------------imaging---------------end-----------------------------

import os,sys
import ConfigParser
import logging
import logging.config

class MUSERConf(object):
    cf = ConfigParser.ConfigParser()
    configFilePath = os.path.join(os.path.dirname(__file__),"muser-config.ini")
    cf.read(configFilePath)

    def __init__(self):
        if not MUSERConf.cf :
            MUSERConf.cf = ConfigParser.ConfigParser()
            MUSERConf.cf.read(MUSERConf.configFilePath)

    @classmethod
    def setConfigFile(cls, filePath):
        cls.configFilePath = filePath
        cls.cf = ConfigParser.ConfigParser()
        cls.cf.read(MUSERConf.configFilePath)

    @classmethod
    def getWebStaticFullPath(cls):
        return cls.cf.get("webapp", "static_full_path")

    @classmethod
    def getWebMuserStaticFullPath(cls):
        return cls.cf.get("webapp", "muser_static_full_path")

    @classmethod
    def getWebTemplatesPath(cls):
        return cls.cf.get("webapp", "templates_path")

    @classmethod
    def getMuserconfServer(cls):
        return cls.cf.get("webapp", "muserconfserver")

    @classmethod
    def getMySQL(cls):
        return cls.cf.get("db", "mysql")

    @classmethod
    def getRedis(cls):
        return cls.cf.get("db", "redis")

    @classmethod
    def getKafka(cls):
        return cls.cf.get("db", "kafka")

    @classmethod
    def getSqliteDir(cls):
        return cls.cf.get("db", "sqliteDir")

    @classmethod
    def getRtServer(cls):
        return cls.cf.get("rtserver", "rtserver")
    @classmethod
    def getCalibrationFileRoot(cls):
        return cls.cf.get("calibration", "calibrationFileRoot")
    @classmethod
    def getCalibrationOutputRoot(cls):
        return cls.cf.get("calibration", "calibrationOutputRoot")

    @classmethod
    def getGeneratePhotoRoot(cls):
        return cls.cf.get("files", "generatePhotoRoot")

    @classmethod
    def getZipRoot(cls):
        return cls.cf.get("files", "zipRoot")
