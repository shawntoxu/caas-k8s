#!/usr/bin/env python
#coding=utf-8
from datetime import datetime
from flask import Flask,request,redirect,abort,Response,render_template
import getopt
import json
import math
import os
import sys
import time
import datetime
import requests

app = Flask(__name__)

#SERVER='172.30.10.185'
#NAMESPACE='image-server'
NAMESPACE='test-vision'

#SERVER='10.2.33.10'
#SERVER='54.169.163.160'
SERVER='172.30.10.122'
SERVER_URL='http://%s:8080'
out_rc_url='/api/v1/namespaces/'+NAMESPACE+'/replicationcontrollers'
out_pod_url='/api/v1/namespaces/'+NAMESPACE+'/pods'
rc_name_url='/api/v1/namespaces/'+NAMESPACE+'/replicationcontrollers/<rc_name>'
port_url='/api/v1/ports/'
is_port_url='/api/v1/ports/<int:port>'

# is lock needed?
class Ports:
    def __init__(self,low,high):
        self.begin = int(low + 1)
        self.end = int(high - 1)
        self.used = [0] * (self.end - self.begin + 1)
        self.pos = 0
        self.defined = dict()

    def is_used(self,port):
        print port,self.begin,self.end
        if port > self.end or port < self.begin:
           return self.defined.has_key(port)
        pos = port - self.begin
        print self.used[pos]
        if (self.used[pos] == 0):
            return False
        else:
            return True

    def get(self):
        i = 0
        v = self.pos
        while True:
            if self.used[v] == 0:
                port = v + self.begin
                #self.used[v] = 1
                self.pos = (v + 1) % (self.end - self.begin + 1)
                break
            v = (v + 1) % (self.end - self.begin + 1)
            i = i + 1
            assert(i <= self.end - self.begin)

        return port

    def delete(self,port):
        if port < self.begin or port > self.end:
            self.defined.pop(port)
        else:
            self.used[port - self.begin] = 0

    def set_used(self,port):
        if port < self.begin or port > self.end:
            self.defined[port] = 1
        else:
            self.used[port - self.begin] = 1

    def show(self):
        for i in range(self.end - self.begin + 1):
            print "%d:%d" % (i,self.used[i])

all_ports = Ports(9000,10000)

def resent_req(url,method):
    if method == 'GET':
        para = request.args
        r = requests.get(url,params=para)
        #print "GET input para%s" % para
    elif method == 'POST':
        para = request.data
        r = requests.post(url,data=para)
        #print "post input para%s" % para
    elif method == 'DELETE':
        r = requests.delete(url)

    strj = r.json()
    #print json.dumps(strj,indent=4)
    if r.status_code == 200 or r.status_code == 201 \
        or r.status_code == 204 or r.status_code == 202:
        return json.dumps(strj,indent=4)
    else:
        print json.dumps(strj,indent=4)

    abort(r.status_code)

def delete_rc(url,rc):
    print "delete rc:%s"%url
    #get rc info
    r = requests.get(url)
    strj = r.json()
    #print json.dumps(strj,indent=4)
    if r.status_code != 200:
        abort(r.status_code)

    #reset rc replicas to 0
    strj['spec']['replicas']=0

    r = requests.put(url,data=json.dumps(strj))

    strj = r.json()
    #print "put res", json.dumps(strj,indent=4)
    if r.status_code != 200:
        abort(r.status_code)

    #get all pod of rc
    pod_url = (SERVER_URL + out_pod_url) % SERVER
    para = {'labelSelector':'name=%s'%rc}
    r = requests.get(pod_url,params=para)
    strj = r.json()
    #print "pod list:%s rc:%s" % (json.dumps(strj,indent=4) , rc)
    for pod in strj['items']:
        for container in pod['spec']['containers']:
            if container.has_key('ports'):
                for port_info in container['ports']:
                    port = port_info['hostPort']
                    #print "reused port",port
                    all_ports.delete(int(port))
        pname = pod['metadata']['name']
        #delete all pod
        purl = (SERVER_URL + out_pod_url + "/%s") % (SERVER,pname)
        requests.delete(purl)

    #delete rc
    return resent_req(url,'DELETE')

def load_ports():
    pod_url = (SERVER_URL + out_pod_url) % SERVER
    r = requests.get(pod_url)
    strj = r.json()
    for pod in strj['items']:
        for container in pod['spec']['containers']:
            if container.has_key('ports'):
                for port_info in container['ports']:
                    port = port_info['hostPort']
                    print "used port:",port
                    all_ports.set_used(int(port))
    print all_ports.defined

@app.route('/')
@app.route('/index')
def index():
    return render_template("index.html")

@app.route(port_url)
def get_port():
    port = all_ports.get()
    return str(port)

@app.route(is_port_url)
def is_port(port):
    if all_ports.is_used(port):
        return "True"
    else:
        return "False"

@app.route(out_rc_url, methods=['GET', 'POST', 'DELETE'])
def list_rc():
    url = (SERVER_URL + out_rc_url) % SERVER
    if request.method == 'DELETE':
        return delete_rc
    elif request.method == 'POST':
        data = request.data
        strj = json.loads(data)
        for container in strj['spec']['template']['spec']['containers']:
            if container.has_key('ports'):
                for port_info in container['ports']:
                    port = port_info['hostPort']
                    #print "used port:",port
                    all_ports.set_used(int(port))

    return resent_req(url, request.method)

@app.route(rc_name_url, methods=['GET', 'POST', 'DELETE'])
def op_rc(rc_name):
    url = (SERVER_URL + out_rc_url + "/%s") % (SERVER,rc_name)
    if request.method == 'DELETE':
        return delete_rc(url, rc_name)
    return resent_req(url, request.method)

@app.route(out_pod_url)
def get_pod():
    url = (SERVER_URL + out_pod_url) % SERVER
    return resent_req(url, request.method)

if __name__ == '__main__':
    load_ports()
    #app.run(host='0.0.0.0',port=8100,debug=True)
    app.run(host='0.0.0.0',port=6800,debug=False)

