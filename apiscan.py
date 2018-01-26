import argparse
import base64
import json
import requests
import time
import ast
import utils.logger as logger
import utils.logs as logs

from core.zapscan import *
from core.parsers import *
from utils.logger import *
from core.login import APILogin
from utils.logger import logger
from utils.config import update_value,get_value,get_allvalues
from modules.cors import cors_main
from modules.auth import auth_check
from modules.rate_limit import rate_limit
from modules.csrf import csrf_check
from core.zap_config import zap_start


def parse_collection(collection_name,collection_type):
    if collection_type == 'Postman':
        parse_data.postman_parser(collection_name)
    elif collection_type == 'Swagger':
        print collection_type
    else:
        print "[-]Failed to Parse collection"
        sys.exit(1)

def add_headers(headers):
    # This function deals with adding custom header and auth value .
    get_auth = get_value('config.property','login','auth_type')
    if get_auth == 'cookie':
        cookie = get_value('config.property','login','auth')
        cookie_dict = ast.literal_eval(cookie)
        cookie_header = {'Cookie': cookie_dict['cookie']}
        headers.update(cookie_header)
    try:
        custom_header = get_value('config.property','login','headers')
        custom_header = ast.literal_eval(custom_header)
        headers.update(custom_header)
    except:
        pass

    return headers

def generate_report():
    # Generating report once the scan is complete.
    result = api_scan.generate_report()
    if result is True:
        print "%s[+]Report is generated successfully%s"% (api_logger.G, api_logger.W)
    else:
        print "%s[-]Failed to generate a report%s"% (api_logger.R, api_logger.W)


def modules_scan(url,method,headers,body,attack):
    '''Scanning API using different engines '''
    print attack
    if attack['zap'] == "Y" or attack['zap'] == "y":
        status = zap_start()
        if status is True:
            api_scan.start_scan(url,method,headers,body)
    
    # Custom modules scan      
    if attack['cors'] == 'Y' or attack['cors'] == 'y':
        cors_main(url,method,headers,body)
    if attack['Broken auth'] == 'Y' or attack['Broken auth'] == 'y':
        auth_check(url,method,headers,body)
    if attack['Rate limit'] == 'Y' or attack['Rate limit'] == 'y':
        rate_limit(url,method,headers,body)
    if attack['csrf'] == 'Y' or attack['csrf'] == 'y':
        csrf_check(url,method,headers,body)


def scan_core(collection_type,collection_name,url,headers,method,body,loginurl,loginheaders,logindata,login_require):
    #Scan API through different engines
    try:
        scan_policy = get_value('scan.property','scan-policy','attack')
        attack = ast.literal_eval(scan_policy)
    
    except Exception as e:
        print "Failed to parse scan property file."
    
    if collection_type and collection_name is not None:
        parse_collection(collection_name,collection_type)
        if login_require is True:
            api_login.verify_login(parse_data.api_lst)
        msg = True
        for data in parse_data.api_lst:
            try:
                url = data['url']['raw']
            except:
                url = data['url']
            headers,method,body = data['headers'],data['method'],''
            if headers:
                try:
                    headhers = add_headers(headers)
                except:
                    pass

            if data['body'] != '':
                body = json.loads(base64.b64decode(data['body']))

            
            modules_scan(url,method,headers,body,attack)        
            #auth_check(url,method,headers,body)

            
    elif url:
        # If the collection is not given as an input.
        if headers is None:
            headers = {'Content-Type' : 'application/json'}
        modules_scan(url,method,headers,body,attack)
        #api_scan.start_scan(url,method,headers,body)

    else:
        print "%s [-]Invalid Collection. Please recheck collection Type/Name %s" %(api_logger.G, api_logger.W)
    #generate_report()

def get_arg(args=None):
        parser = argparse.ArgumentParser(description='REST API Security testing Framework')
        parser.add_argument('-c', '--collection_type',
                            help='Type of API collection',
                            default='Postman',choices=('Postman', 'Swagger'))
        parser.add_argument('-n', '--collection_name',
                            help='Type of API collection')
        parser.add_argument('-u', '--url',
                            help='URL of target API')
        parser.add_argument('-headers', '--headers',
                            help='Custom headers.Example: {"token" : "123"}')
        parser.add_argument('-method', '--method',
                            help='HTTP request method',
                            default='GET',choices=('GET', 'POST'))
        parser.add_argument('-b', '--body',
                            help='Request body of API')
        parser.add_argument('-l', '--loginurl',
                            help='URL of login API')
        parser.add_argument('-H', '--loginheaders',
                            help='Headers should be in a dictionary format. Example: {"accesstoken" : "axzvbqdadf"}')
        parser.add_argument('-d', '--logindata',
                            help='login data of API')
    

        results = parser.parse_args(args)
        return (results.collection_type,
                results.collection_name,
                results.url,
                results.headers,
                results.method,
                results.body,
                results.loginurl,
                results.loginheaders,
                results.logindata,
                )

def main():
    collection_type,collection_name,url,headers,method,body,loginurl,loginheaders,logindata = get_arg(sys.argv[1:])
    if loginheaders is None:
            loginheaders = {'Content-Type' : 'application/json'}
    if collection_type and collection_name and loginurl and loginmethod and logindata:
        # Login data is given as an input. 
        api_login.fetch_logintoken(loginurl,loginmethod,loginheaders,logindata)
        login_require = False
    elif collection_type and collection_name and loginurl:
        # This will first find the given loginurl from collection and it will fetch auth token. 
        parse_collection(collection_name,collection_type)
        try:
            loginurl,lognheaders,loginmethod,logidata = api_login.parse_logindata(loginurl)
        except:
           print "[-]%s Failed to detect login API from collection %s " %(api_logger.R, api_logger.W)
           sys.exit(1)
        api_login.fetch_logintoken(loginurl,loginmethod,loginheaders,logindata)
        login_require = False
    elif loginurl and loginmethod:
        api_login.fetch_logintoken(loginurl,loginmethod,loginheaders,logindata)
        login_require = False
    elif collection_type and collection_name and headers:
        #Custom headers
        update_value('login','header',headers)
        login_require = False
    elif url and collection_name and headers:
        #Custom headers
        update_value('login','header',headers)
        login_require = False
    elif url:
        if headers is None:
            headers = {'Content-Type' : 'application/json'}
        if method is None:
            method = "GET"
       
        login_require = False
    else:
        login_require = True

    # Configuring ZAP before starting a scan
    get_auth = get_value('config.property','login','auth_type')

    scan_core(collection_type,collection_name,url,headers,method,body,loginurl,loginheaders,logindata,login_require) 


if __name__ == '__main__':
    
    api_scan = zap_scan()
    api_login = APILogin()
    parse_data = PostmanParser()
    api_logger = logger()
    api_logger.banner()
    main()