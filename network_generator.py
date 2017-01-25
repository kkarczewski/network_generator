#! /usr/bin/env python3.4
#! -*- coding: utf-8 -*-
'''
Created on 27 lip 2015

@author: kamil@justnet.pl
'''

# #############################################################################
# standard modules (moduly z biblioteki standarowej pythona)
# #############################################################################
import os
import sys
import re
import time
import argparse
import subprocess
import pipes
import getpass
import string
import ipaddress
import socket
import struct
import xml.etree.ElementTree as ET
import datetime
import base64
import json

NAME = __file__
SPLIT_DIR = os.path.dirname(os.path.realpath(NAME))
SCRIPT_DIR = SPLIT_DIR + '/.' + os.path.basename(NAME)
LIB_DIR = SCRIPT_DIR + '/cache/lib/'
TMP_DIR = SPLIT_DIR + '/cache'
sys.path.insert(0,LIB_DIR)
#List of lib to install
import_list = [
   ('sqlalchemy','1.0.8','SQLAlchemy-1.0.8.egg-info'),
   ('colorama','0.3.3','colorama-0.3.3.egg-info'),
#   ('deepdiff','0.5.7','deepdiff-0.5.7.egg-info'),
   ('pymysql','0.6.7','PyMySQL-0.6.7.dist-info')]
for line in import_list:
   try:
      if os.path.isdir(LIB_DIR+line[2]):
         pass
#         print('Found installed '+line[0]+line[1]+' in '+line[2])
      else:
         try:
            import pip
         except:
            print("Use sudo apt-get install python3-pip")
            sys.exit(1)
         print('No lib '+line[0]+'-'+line[1])
         os.system("python"+sys.version[0:3]+" -m pip install '"+line[0]+'=='+line[1]+"' --target="+LIB_DIR)
      module_obj = __import__(line[0])
      globals()[line[0]] = module_obj
   except ImportError as e:
      print(line[0]+' is not installed')

# #############################################################################
# constants, global variables
# #############################################################################
OUTPUT_ENCODING = 'utf-8'
DIRECTORY = './'
TEMP_PATH = SCRIPT_DIR+'/cache/'
LOGGER_PATH = SCRIPT_DIR+'/logfile.xml'
LOG_VERSION = 1.0
MAIN_DB = 'network_generator'
CURRENT_STATE = 'current.json'
TABLES = ('punkty_dostepu','sieci')
# #############################################################################
# functions
# #############################################################################
#CZYTANIE Z PLIKU
def readfile(file_name):
   try:
      with open(file_name, 'r') as file:
         templines = [line.rstrip() for line in file]
         lines=([])
         for line in templines:
            if not '#' in line:
               lines.append(line)
   except (IOError, OSError):
      print >> sys.stderr, "Can't open file."
      sys.exit(1)
   return lines

def writefile(path_to_conf,file_name,data):
   if os.path.exists(path_to_conf):
      try:
         with open(path_to_conf+file_name,'w') as fileout:
            for line in data:
               fileout.writelines(line+'\n')
      except(IOError,OSError):
         print_err("Can't write to file.")
         sys.exit(1)
   else:
      print_err("Can't write to file. There are no path that you specified")

#Kolorowanie ok
def print_ok(output):
   print(colorama.Fore.GREEN+output,colorama.Fore.RESET)

#Kolorowanie błędu
def print_err(error):
   print(colorama.Fore.RED+error,colorama.Fore.RESET)

#Kolorowanie warningów
def print_war(warning):
   print(colorama.Fore.YELLOW+warning,colorama.Fore.RESET)

# pretty print do logowania
def indent(elem, level=0):
  i = "\n" + level*"  "
  if len(elem):
    if not elem.text or not elem.text.strip():
      elem.text = i + "  "
    if not elem.tail or not elem.tail.strip():
      elem.tail = i
    for elem in elem:
      indent(elem, level+1)
    if not elem.tail or not elem.tail.strip():
      elem.tail = i
  else:
    if level and (not elem.tail or not elem.tail.strip()):
      elem.tail = i

#Logowanie
def my_logger(ERROR_FLAG,subcmd,outmsg):
   id_log = 1
   if not os.path.exists(LOGGER_PATH):
      root = ET.Element('root')
      root.set('version','1.0')
   else:
      tree = ET.parse(LOGGER_PATH)
      root = tree.getroot()
      for child in root:
         id_log+=1
   log = ET.SubElement(root, 'log')
   log.set('id_log',str(id_log))
   date = ET.SubElement(log,'date')
   date.text = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')
   cmdline = str()
   for line in sys.argv:
      cmdline += line+' '
   command = ET.SubElement(log,'command')
   command.set('encoding','plain')
   command.text = cmdline
   subcommands = ET.SubElement(log,'subcommands')
   subcommands.set('error_flag',ERROR_FLAG)
   subcmd_str=str()
   for one in subcmd:
      subcmd_str+=one+','
   subcommands.text = subcmd_str[:-1]
   outmsg_str = str()
   for one in outmsg:
      outmsg_str+=one+','
   msg = (base64.b64encode(outmsg_str.encode(OUTPUT_ENCODING))).decode(OUTPUT_ENCODING)
   output = ET.SubElement(log,'output')
   output.set('encoding','base64')
   output.text = msg
   indent(root)
   if not os.path.exists(LOGGER_PATH):
      tree = ET.ElementTree(root)
   tree.write(LOGGER_PATH,
              encoding=OUTPUT_ENCODING,
              xml_declaration=True,
              method='xml')

#Wykonywanie poleceń w terminalu
def os_call(*args,progress_char='*',verbose=1):
   n = 0
   done_cmd = list()
   out = list()
   for cmd in args:
      p = subprocess.Popen(cmd,
              stdout=subprocess.PIPE,
              stderr=subprocess.PIPE,
              shell=True,
              cwd=DIRECTORY)
      (output,err) = p.communicate()
      n = n+1
      ast = progress_char*n
      if err or 'ERROR' in str(output) or 'Exception' in str(output):
         done_cmd.append(cmd)
         ERROR_FLAG = 'T'
         print_err(cmd)
         if err:
            print_err(err.decode(OUTPUT_ENCODING))
            out.append(err.decode(OUTPUT_ENCODING))
            break
         else:
            print_err(output.decode(OUTPUT_ENCODING))
            out.append(output.decode(OUTPUT_ENCODING))
            break
      else:
         ERROR_FLAG = 'F'
         done_cmd.append(cmd)
         out.append(output.decode(OUTPUT_ENCODING))
         if verbose == 2:
            print(ast,end="\r")
            time.sleep(1)
            print_ok(cmd)
            print_ok(output.decode(OUTPUT_ENCODING))
         elif verbose == 1:
            print_ok(output.decode(OUTPUT_ENCODING))
         else:
            print(ast,end='\r')
   return ERROR_FLAG,done_cmd,out

# JSON WRITE/READ
def json_write(file_name,one,two):
   with open(file_name,'w') as jsonfile:
      json.dump({'engine':engine_text,'punkty_dostepu':one,'sieci':two},jsonfile, sort_keys=True,indent=4,separators=(',', ': '))
def json_read(file_name):
   with open(file_name) as jsonfile:
      data = json.load(jsonfile)
   return data

def simple_query(query,values,database):
   try:
#      print(engine_text)
      engine = sqlalchemy.create_engine(engine_text)      
      connection = engine.connect()
      query = query.bindparams(**values)
      result = connection.execute(query).fetchall()
      data = str()
      for row in result:
         data+=str(row)+';'
      connection.close()
      data = data[1:-2].split(');(')
      return data
   except Exception as e:
      print(e)
      sys.exit(print_err("Connection error."))

def make_dir(ap_id,iface,CONF_DIR):
   path = CONF_DIR+ap_id+'/'+iface
   if not os.path.exists(path):
      os.makedirs(path)
   
def make_conf_interface(one_network,CONF_DIR):
   config = dict(ID=one_network[0],IFACE = one_network[8])
   temp = string.Template('#$ID,auto $IFACE,iface $IFACE inet static')
   prepared = temp.safe_substitute(config)
   prepared = prepared.split(',')
   path_to_conf = CONF_DIR+one_network[0]+'/'
   file_name = one_network[8]+'.conf'
   return prepared,path_to_conf,file_name

def make_conf_vlan(one_vlan,CONF_DIR):
   if len(one_vlan)==11:
      temp = string.Template("auto $IFACE.$VLAN,iface $IFACE.$VLAN inet static,  address $ADDRESS,  netmask $NETMASK,  broadcast $BROADCAST,  network $NETWORK")
      start_end=list()
      start_end.append('START_IP: '+one_vlan['IP_START'])
      start_end.append('END_IP: '+one_vlan['IP_END'])
   else:
      temp = string.Template("auto $IFACE.$VLAN,iface $IFACE.$VLAN inet manual,    up ip li set up dev $IFACE.$VLAN,    down ip li set up dev $IFACE.$VLAN")
      start_end=''
   prepared = temp.safe_substitute(one_vlan)
   prepared = prepared.split(',')
   path_to_conf=CONF_DIR+one_vlan['ID']+'/'+one_vlan['IFACE']+'/'
   file_name = one_vlan['IFACE']+'-'+one_vlan['VLAN']+one_vlan['UNIQUE']+'.conf'
   return path_to_conf,file_name,prepared,start_end

def get_all_data(args,id_ap):
   try:
      params = dict()
      if args == 'punkty_dostepu' and id_ap=='':
         sql = simple_query(sqlalchemy.text('''
SELECT id,
 typ,
 nazwa,
 opis,
 mac,
 INET_NTOA(ip),
 INET_NTOA(maska),
 snmp_community,
 ExtractValue(content, '/root/interfaces/interface/@name'),
 ExtractValue(content,'/root/interfaces/interface/vlans/vlan')
FROM 
 '''+args+'''
WHERE 
 typ !="pppoe"'''),params,MAIN_DB)
         sql_pure = simple_query(sqlalchemy.text('SELECT * FROM '+args+" WHERE typ !='pppoe'"),params,MAIN_DB)
      elif args == 'punkty_dostepu' and id_ap:
         params['ID'] = id_ap
         sql = simple_query(sqlalchemy.text('''
SELECT
 id,
 typ,
 nazwa,
 opis,
 mac,
 INET_NTOA(ip),
 INET_NTOA(maska),
 snmp_community,
 ExtractValue(content, '/root/interfaces/interface/@name'),
 ExtractValue(content,'/root/interfaces/interface/vlans/vlan')
FROM 
 '''+args+'''
WHERE
 typ !="pppoe" AND
 id=:ID'''),params,MAIN_DB)
         sql_pure = simple_query(sqlalchemy.text('''
SELECT * 
FROM '''+args+'''
WHERE typ !='pppoe' and id=:ID'''),params,MAIN_DB)
      else:
         sql = simple_query(sqlalchemy.text('''
SELECT
 id,
 punkt_dostepu_id,
 INET_NTOA(network),
 INET_NTOA(router),
 INET_NTOA(broadcast),
 INET_NTOA(maska),
 ExtractValue(content,'/root/interface'),
 ExtractValue(content,'/root/vlan'),
 INET_NTOA(adres_start),
 INET_NTOA(adres_end) 
FROM '''+args+'''
WHERE
 punkt_dostepu_id !=32 AND
 punkt_dostepu_id != 33'''),params,MAIN_DB)
         sql_pure = simple_query(sqlalchemy.text('''
SELECT * 
FROM '''+args+'''
WHERE punkt_dostepu_id !=32 AND
 punkt_dostepu_id != 33'''),params,MAIN_DB)
      return sql,sql_pure
   except Exception as e:
      print(e)

def extract(one_xml,table):
   root = ET.fromstring(one_xml)
   iface = dict()
   all_vlan = list()
   all_ifaces = list()
   if table == 'sieci':
      for child in root:
         if child.tag == 'interface':
            iface['iface'] = child.text
         if child.tag == 'vlan':
            iface['vlan'] = child.text
   elif table == 'punkty_dostepu':
      for child in root:
         for ifaces in child:
            all_ifaces.append(ifaces.attrib['name'])
            for vlans in ifaces:
               for vlan in vlans:
                  all_vlan.append(vlan.text)
            iface[ifaces.attrib['name']] = all_vlan.copy()
            all_vlan.clear()
         iface['iface'] = all_ifaces.copy()
         all_ifaces.clear()
   else:
      for child in root:
         print(child.tag, child.text, child.attrib)
   return iface 

def get_vlan_for_iface(main_table):
   ifaces = list()
   for one in main_table:
      one = one.split(', ')
      del one[-1]
      one[-1] = one[-1][1:-1].split(' ')
      for iface in one[-1]:
         temp = list()
         params = dict(ID=one[0],IFACE=iface)
         vlans = simple_query(sqlalchemy.text('''
SELECT ExtractValue(content,"/root/interfaces/interface[@name=:IFACE]/vlans/vlan")
FROM punkty_dostepu 
WHERE id=:ID'''),params,MAIN_DB)
         vlans = vlans[0][1:-2].split(' ')
         temp.extend(one[:-1])
         temp.append(iface)
         temp.append(vlans)
         ifaces.append(temp.copy())
   return ifaces

def restore_vlan_conf(ap,one_vlan,one_network,current_networks):
   vlan_conf = list()
   for one in current_networks:
      one = one.split(', ')
      current = extract(one[9][1:-1],'sieci')
      if one_network[0] == one[2] and one_vlan == current['vlan'] and one_network[8] == current['iface']:
         two = list()
         two = one[:5]
         two.append(one[7])
         two.append(one[8])
         two.append(one[5])
         two.append(one[6])
         for n in range(3,9):
            two[n] = "'"+socket.inet_ntoa(struct.pack('!I',int(two[n])))+"'"
         two.insert(7,"'"+current['iface']+"'")
         two.insert(8,"'"+current['vlan']+"'")
         del two[1]
         two = (', ').join(two)
         vlan_conf.append(two)
   return vlan_conf

def get_conf_vlans(one_network,current_networks):
   list_vlan_conf = list()
   all_vlan = list()
   if 'restore' in args:
      vlan_conf = list()
   else:
      sql_vlan = sqlalchemy.text('''
SELECT
 id,
 punkt_dostepu_id,
 INET_NTOA(network),
 INET_NTOA(router),
 INET_NTOA(broadcast),
 INET_NTOA(maska),
 ExtractValue(content,'/root/interface') AS :CELL,
 ExtractValue(content,'/root/vlan') AS :CELLS,
 INET_NTOA(adres_start),
 INET_NTOA(adres_end) 
FROM
 sieci 
WHERE
 punkt_dostepu_id=:AP_ID AND
 ExtractValue(content,'root/interface')=:IFACE AND
 ExtractValue(content,'/root/vlan')=:VLAN''')
   for one_vlan in one_network[9]:
      if 'restore' in args:
         vlan_conf = restore_vlan_conf(one_network[0],one_vlan,one_network,current_networks)
      else:
         data_vlan = dict(CELL='iface',CELLS='vlan',
                          AP_ID=one_network[0],IFACE=one_network[8],
                          VLAN=one_vlan)
         vlan_conf = simple_query(sql_vlan,data_vlan,MAIN_DB)
      prepared_data = dict()
      for one in range(len(vlan_conf)):
         all_vlan.append(vlan_conf[one])
         if one == 0:
            prepared_data['UNIQUE'] = ''
         else:
            prepared_data['UNIQUE'] = ':'+str(one)
         if vlan_conf[one] == '':
            prepared_data['ID'] = one_network[0] 
            prepared_data['IFACE'] = one_network[8]
            prepared_data['VLAN'] = one_vlan
            list_vlan_conf.append(prepared_data.copy())
            print_err('Not a conf for vlan '+prepared_data['VLAN']+' on iface '+prepared_data['IFACE']+' on ap '+prepared_data['ID'])
            prepared_data.clear()
         else:
            vlan_conf[one] = vlan_conf[one].split(', ')
            prepared_data['ID'] = vlan_conf[one][1]
            prepared_data['IFACE'] = vlan_conf[one][6][1:-1] 
            prepared_data['VLAN'] = vlan_conf[one][7][1:-1] 
            prepared_data['ADDRESS'] = vlan_conf[one][3][1:-1] 
            prepared_data['NETMASK'] = vlan_conf[one][5][1:-1]
            prepared_data['BROADCAST'] = vlan_conf[one][4][1:-1]
            prepared_data['NETWORK'] = vlan_conf[one][2][1:-1] 
            prepared_data['ID_VLAN'] = vlan_conf[one][0]
            prepared_data['IP_START'] = vlan_conf[one][8][1:-1]
            prepared_data['IP_END'] = vlan_conf[one][9][1:-1]
            list_vlan_conf.append(prepared_data.copy())
            prepared_data.clear()
   return list_vlan_conf,all_vlan

def exec_settings(iface,vlan):
   try:
      commands = list()
      if vlan == '':
         commands.append("ip li add link "+iface+' name '+iface)
         commands.append("ip li set up dev "+iface)
      else:
         commands.append("ip li add link "+iface+' name '+iface+'.'+vlan+' type vlan id '+vlan)
         commands.append("ip li set up dev "+iface+'.'+vlan)
      return commands
   except Exception as e:
      print(e)
      return False

def create_data(data,tables,path,name):
   punkty,punkty_pure = get_all_data(tables[0],'')
   sieci,sieci_pure = get_all_data(tables[1],'')
   json_write(path+name,punkty_pure,sieci_pure)

def check_all(current,new_one):
   changes = list()
   if current == new_one:
      print_ok('No changes in table.')
   else:
#      print_ok("Checking that current table is in main table.")
      for one in current:
         if not one in new_one:
#            print("IN CURRENT TABLE && NOT IN MAIN TABLE")
            changes.append("NOT IN MAIN TABLE, "+one)
#         else:
#            print("IN CURRENT TABLE AND IN MAIN TABLE")
#      print_ok("Checking that main table is in current table.")
      for one in new_one:
         if not one in current:
#            print("IN MAIN TABLE AND NOT IN CURRENT TABLE")
            changes.append("NOT IN CURRENT TABLE, "+one)
#         else:
#            print("IN MAIN TABLE AND IN CURRENT TABLE")
   return changes

def one_config(one_conf,CONF_DIR,current_networks):
   cmd = list()
   list_all_vlans = list()
   vlans_conf,all_vlans = get_conf_vlans(one_conf,current_networks)
   list_all_vlans.extend(all_vlans)
   for one_vlan in vlans_conf:
      path_conf,file_name,prepared, start_end = make_conf_vlan(one_vlan,CONF_DIR)
      writefile(path_conf,file_name,prepared)
      if 'verbose' in args:
         print('Added '+path_conf+file_name)
      if execute == True and 'update' in args:
         one_cmd = exec_settings(one_vlan['IFACE'],one_vlan['VLAN'])
         cmd.extend(one_cmd)
#         os_call(cmd,progress_char='*',verbose=2)
#         print(cmd) # Lista poleceń do wykonania przez exec
   return list_all_vlans

def processing_changed(changed_data,CONF_DIR):
   for one in changed_data:
      one = one.split(', ')
# NOT IN MAIN SIECI usuwanie 1/eth2/eth2-200*(.conf_addr,:1,:2,:3.conf)
      if one[0] == 'NOT IN MAIN sieci':
         vlans = extract(one[10][1:-1],'sieci')
         os.system("rm -r "+CONF_DIR+one[3]+'/'+vlans['iface']+'/'+vlans['iface']+'-'+vlans['vlan']+'*')
         if 'verbose' in args:
            print('Deleted '+CONF_DIR+one[3]+'/'+vlans['iface']+'/'+vlans['iface']+'-'+vlans['vlan']+'*')
# NOT IN MAIN PUNKTY_DOSTEPU usuwanie folderu ./1/
      if one[0] == 'NOT IN MAIN punkty_dostepu':
         os.system("rm -r "+CONF_DIR+one[1])
         if 'verbose' in args:
            print('Deleted '+CONF_DIR+one[1])
# NOT IN CURRENT SIECI zapisywanie nowych plików 
      if one[0] == 'NOT IN CURRENT sieci':
         one_network = list()
         vlans = list()
         data = extract(one[10][1:-1],'sieci')
         one_network.extend(one[3:-1])
         one_network.insert(1,one[1])
         one_network.append(data['iface'])
         vlans.append(data['vlan'])
         one_network.append(vlans)
         one_config(one_network,CONF_DIR,'')
# NOT IN CURRENT PUNKTY_DOSTEPU zapisywanie całymi folderami 
      if one[0] == 'NOT IN CURRENT punkty_dostepu':
         aps = list()
         one_aps = list()
         one[9] = one[9].replace('\\n','')
         iface = extract(one[9][1:-1],'punkty_dostepu')
         one_aps = one[1:8]
         one_aps.append(str(None))
         ifaces = str(iface['iface'])
         ifaces = ifaces[1:-1].replace("'",'').replace(',','')
         one_aps.append("'"+ifaces+"'")
         one_aps.append(str('vlany'))
         one_aps = (', ').join(one_aps)
         aps.append(one_aps)
         ifaces = get_vlan_for_iface(aps)
         for one in ifaces:           
            make_dir(one[0],one[8],CONF_DIR)
            if 'verbose' in args:
               print('Added '+CONF_DIR+one[0]+'/'+one[8])
            one_iface,path_to_out,name = make_conf_interface(one,CONF_DIR)
            if 'verbose' in args:
               print('Added '+path_to_out+name)
            writefile(path_to_out,name,one_iface)
            if execute == True:
               exec_settings(one[8],'')
            one_config(one,CONF_DIR,'')

def not_existing_vlan(all_vlans,all_table):
   all_vlans = [x for x in all_vlans if x]
   all_vlans.sort()
   all_table.sort()
#   del all_vlans[30]
   if not all_table == all_vlans:
      for one in all_table:
         if one not in all_vlans:
#            print_war(one)
            one = one.split(', ')
            print_war("Conf for not existing vlan "+one[7][1:-1]+" on iface "+one[6][1:-1]+" for ap "+one[1])

# #############################################################################
# operations
# #############################################################################

def opt_init(args,CONF_DIR,force,execute):
   try:
      if os.path.exists(CONF_DIR) and force == False:
         if len(os.listdir(CONF_DIR)) > 2 and force == False and CONF_DIR == './':
            sys.exit(print_war("USE -- force-update/-f"))
         elif len(os.listdir(CONF_DIR)) > 0 and force == False and CONF_DIR != './':
            sys.exit(print_war("USE --force-update/-f"))
      punkty,punkty_pure = get_all_data(TABLES[0],'')
      all_sieci, all_sieci_pure = get_all_data(TABLES[1],'')
      all_vlans_all_ifaces = list()
      ifaces = get_vlan_for_iface(punkty)
      for one in ifaces:
         make_dir(one[0],one[8],CONF_DIR)
         one_iface,path_to_out,name = make_conf_interface(one,CONF_DIR)
         writefile(path_to_out,name,one_iface)
         list_all_vlans_for_iface = one_config(one,CONF_DIR,'')
         all_vlans_all_ifaces.extend(list_all_vlans_for_iface)
      not_existing_vlan(all_vlans_all_ifaces,all_sieci)
      create_data('',TABLES,CONF_DIR,CURRENT_STATE)
      return True
   except Exception as e:
      print(e)
      return False

def opt_update(args,CONF_DIR,execute):
   try:
      if os.path.exists(CONF_DIR+CURRENT_STATE):
         data = json_read(CONF_DIR+CURRENT_STATE)
      else:
         print_err("There is no configuration or you specified wrong path.")
         return False
      changed_data = list()
# SPRAWDZANIE ZMIAN POMIĘDZY TABELAMI CURRENT I MAIN
      for table in TABLES:
         current = data.get(table)
         new_main,new_main_pure = get_all_data(table,'')
         one_change = check_all(current,new_main_pure)
         for two in one_change:
            two = two.replace('TABLE',table)
            changed_data.append(two)
# DZIAŁANIA DLA ZMIAN
      processing_changed(changed_data,CONF_DIR)
      create_data('',TABLES,CONF_DIR,CURRENT_STATE)
      return True
   except Exception as e:
      print(e)
      return False

def opt_restore(args,CONF_DIR):
   try:
      if os.path.exists(CONF_DIR+CURRENT_STATE):
         data = json_read(CONF_DIR+CURRENT_STATE)
      else:
         print_err("There is no configuration or you specified wrong path.")
         return False
      opt_clear(args,CONF_DIR)
      current_networks = data.get(TABLES[1])
      current_apses = data.get(TABLES[0])
      list_of_aps = list()
      for one in current_apses:
         aps = list()
         one = one.split(', ')
         one[8] = one[8].replace('\\n','')
         xml_data = extract(one[8][1:-1],'punkty_dostepu')
         del one[8]
         for one_iface in xml_data['iface']:
            one_aps = list()
            one_aps.extend(one)
            one_aps.append(one_iface)
            one_aps.append(xml_data[one_iface])
            aps.append(one_aps.copy())
         list_of_aps.extend(aps.copy())
      for one in list_of_aps:
         make_dir(one[0],one[8],CONF_DIR)
         one_iface,path_to_out,name = make_conf_interface(one,CONF_DIR)
         writefile(path_to_out,name,one_iface)
         one_config(one,CONF_DIR,current_networks)
      json_write(CONF_DIR+CURRENT_STATE,current_apses,current_networks)
   except Exception as e:
      print(e)
      return False

def opt_clear(args, conf_dir):
   try:
      if os.path.exists(conf_dir):
         os.system("rm -r "+conf_dir)
      else:
         print_err('There is already clear or you specified wrong path.')
   except Exception as e:
      print(e)

def opt_access_point(args,CONF_DIR):
   try:
      punkty,punkty_pure = get_all_data(TABLES[0],args)
      if punkty == ['']:
         sys.exit(print_err('There is no access point with this id.'))
      ifaces = get_vlan_for_iface(punkty)
      for one in ifaces:
         make_dir(one[0],one[8],CONF_DIR)
         one_iface,path_to_out,name = make_conf_interface(one,CONF_DIR)
         writefile(path_to_out,name,one_iface)
         one_config(one,CONF_DIR,'')
   except Exception as e:
      print(e)

def opt_help():
   parser.print_help()
   msg = 'Printed help'
   msg = (base64.b64encode(('Printed help').encode(OUTPUT_ENCODING))).decode(OUTPUT_ENCODING)
   return msg

def opt_db_engine(args,CONF_DIR):
   global engine_text
   if 'init' in args or 'access_point' in args:
      config = dict(user=args.user,host=args.host,port=args.port)
      if not 'schema' in args:
         sys.exit(print_err("Database schema is required."))
      else:
         config['schema'] = args.schema
      if args.password == None:
         config['password'] = getpass.getpass('Password to database: ')
      else:
         config['password'] = args.password
      temp = string.Template('mysql+pymysql://$user:$password@$host$port/$schema')
      engine_text = temp.safe_substitute(config)
      if 'localhost' in engine_text:
         engine_text+='?unix_socket=/var/run/mysqld/mysqld.sock'
   else:
      data = json_read(CONF_DIR+CURRENT_STATE)
      engine_text = data['engine']
   return engine_text 

# #############################################################################
# main app 
# #############################################################################
if __name__ == '__main__':
# Czytanie arugmentów
   parser = argparse.ArgumentParser(
      prog='network_generator.py',
      description='Generating config file for network interfaces and vlan.',
      epilog='''Example of usage:
      $ ./network_generator.py -cd ./conf init
      $ ./network_generator.py -u user -p -H hostname -O 134 init
      $ ./network_generator.py clear
      $ ./network_generator.py -cd ./conf clear
      $ ./network_generator.py -ap 41''',
      argument_default=argparse.SUPPRESS,
      formatter_class=argparse.RawTextHelpFormatter)
# SUBPARSER
   subparsers = parser.add_subparsers()
# INIT
   parser_init = subparsers.add_parser('init',
      help = '''Create json file with current database state
in it before generating configuration file.
With -f overwrite old file.''')
   parser_init.add_argument('init',action='store_true',
      help = 'Create json file with current database state in it. Then generating configuration file structure. Returned files with .')
# CLEAR
   parser_clear = subparsers.add_parser('clear',
      help = '''Drop temporary database and all configuration
file structure.''')
   parser_clear.add_argument('clear',
      action = 'store_true',
      help = 'Drop temporary database and all configuration file structure.')
# UPDATE
   parser_update = subparsers.add_parser('update',
      help = '''Update temporary database and create updated
configuration file.''')
   parser_update.add_argument('update',
      action = 'store_true',
      help = 'Update temporary database and create updated configuration file.')
# RESTORE
   parser_restore = subparsers.add_parser('restore',
      help = '''Generate configuration file from temporary
database instead of main database.''')
   parser_restore.add_argument('restore',
      action='store_true',
      help = 'Generate configuration file from temporary database instead of main database.')
# INIT force_update
   parser_init.add_argument('-f','--force_update',
      default=False,
      action='store_true',
      help = '''Remove current configuration file.
Then create new one like
in init.''')
# ACCESS POINT
   parser.add_argument('--access_point','-ap',
      help = '''Generate configuration file for all device for
access point with id that you specified without
checking differences in temporary database.''')
   parser.add_argument('--conf-dir','-cd',
      default = './config/',
      help = '''Directory to create configuration file
structure. Use before positional args.''')
   parser.add_argument('--exec','-e',
      default = False,
      action = 'store_true',
      help = '''Execute command for system like ip li add. Use
before positional args.''')
   parser.add_argument('--user','-u',
      default='jsql',
      help = 'Database user name/login..')
   parser.add_argument('--password','-p',
      default = '',
      nargs = '?',
      help = '''Database user password, no password as default,
if used without value you will be asked to write
password in prompt.''')
   parser.add_argument('--host','-H',
      default = 'localhost',
      help = 'Database url/ip address. Default localhost.')
   parser.add_argument('--port','-O',
      default = '',
      help = 'Database port number.')
   parser.add_argument('--schema','-s',
      default = 'network_generator',
      help = 'Database schema name.')
   parser.add_argument('--verbose','-v',
      action = 'store_true',
      help = 'Printing added,removed and updated file.')
   argv = sys.argv[1:]
   args = parser.parse_args(argv)
   try:
#      print(args)
      if not (args.conf_dir).endswith('/'):
         args.conf_dir=args.conf_dir+'/'
      config_dir = args.conf_dir
      execute = args.exec 
      if not len(sys.argv) > 1 or 'help' in args:
         opt_help()
      elif 'init' in args:
         force = args.force_update
         engine_text = opt_db_engine(args,config_dir)
         opt_init(args.init,config_dir,force,execute)
         print_ok("Done")
      elif 'clear' in args:
         opt_clear(args.clear,config_dir)
         print_ok("Done")
      elif 'restore' in args:
         opt_db_engine(args,config_dir)
         opt_restore(args.restore,config_dir)
         print_ok("Done")
      elif 'update' in args:
         engine_text = opt_db_engine(args,config_dir)
         opt_update(args.update,config_dir,execute)
         print_ok("Done")
      elif 'access_point' in args:
         engine_text = opt_db_engine(args,config_dir)
         opt_access_point(args.access_point,config_dir)
         print_ok("Done")
      else:
         opt_help()
   except Exception as e:
      cmd = str()
      for one_arg in sys.argv:
         cmd+=one_arg+' '
      list_cmd=list()
      list_cmd.append(cmd)
      err_msg = str(e)
      my_logger('T',list_cmd,err_msg)
      print(e)
