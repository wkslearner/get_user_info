from get_user_info.config import init_app
from ti_daf import SqlTemplate, sql_util, TxMode
import pandas as pd
from datetime import datetime
from get_user_info.data_merge.send_email import EmailSend
import datetime as dt
from ti_lnk.ti_lnk_client import TiLnkClient
from ti_daf.sql_context import  select_rows_by_sql
from ti_daf.sql_tx import session_scope
import os

class DatabaseOperator():
    def __init__(self, ns_config):
        init_app()
        self.ns_server_id = ns_config


    # 根据sql_text查询记录
    def query_record(self, sql_text, return_type=None, params={}):
        with session_scope(tx_mode=TxMode.NONE_TX, ns_server_id=self.ns_server_id) as session:
            if return_type == 'List':
                self.row_result = select_rows_by_sql(sql_text, params, max_size=-1)
            else:
                self.row_result = session.execute(sql_text,params)

            return self.row_result

    '''
    # 删除主键对应的记录
    def delete_record(self, table_name, id):
        with session_scope(tx_mode=TxMode.NONE_TX, ns_server_id=self.ns_server_id) as session:
            delete_by_id(table_name, id)

    # 批量插入记录
    def batch_insert_record(self, table_name, insert_values):
        with session_scope(tx_mode=TxMode.NONE_TX, ns_server_id=self.ns_server_id) as session:
            batch_insert(table_name, insert_values)
    '''

    # 批量更新记录
    def batch_update_record(self, batch_update_values, table_name, id):
        with session_scope(tx_mode=TxMode.NONE_TX, ns_server_id=self.ns_server_id) as session:
            sql_util.batch_update(table_name, id, batch_update_values)




def get_mobile_phone(partyId):
    init_app()

    db=DatabaseOperator('/python/db/ac_cif_db')

    sql = '''
            select ao.corporateRepresentUserName phoneNumber from ac_cif_db.OrgParty ao
            where ao.partyId = :partyId
        '''
    #db = sql_util.select_rows_by_sql(sql_text=sql,sql_paras={},ns_server_id='/python/db/ac_cif_db', max_size=-1)
    param = dict()
    param['partyId'] = partyId
    row_list = db.query_record(sql, params=param)
    phone_num = None
    for row in row_list:
        phone_num = row['phoneNumber']

    if phone_num is None:
        return 0

    service_group = 'ac-ums.admin-srv'
    service_id = 'me.andpay.ac.ums.api.UserManagementService'
    user = TiLnkClient.call_lnk_srv(service_group, service_id, 'getUserByUserName', phone_num, ns_server_id=None)

    if user is None:
        return 0
    else:
        return user['userName']


def data_merge(user_df):
    user_list=list(user_df['partyid'])

    phone_list=[]
    for partyid in user_list:
        phone_number=get_mobile_phone(partyid)
        phone_list.append([partyid,phone_number])

    phone_df=pd.DataFrame(phone_list,columns=['partyid','phone_number'])

    return phone_df


def email_task():
    path = os.path.dirname(__file__)
    #path=path+

    nodeal_df=pd.read_excel(path)
    res_df = data_merge(nodeal_df)


    excel_writer=pd.ExcelWriter('/home/andpay/data/excel/helprepay_nodeal_userlist.xlsx',engine='xlsxwriter')
    res_df.to_excel(excel_writer,index=False)
    excel_writer.save()


    subject = 'helprepay_nodeal_userlist'
    to_addrs = ['kesheng.wang@andpay.me']
    body_text = 'helprepay_nodeal_userlist'
    attachment_file = "/home/andpay/data/excel/helprepay_nodeal_userlist.xlsx"

    EmailSend.send_email(subject, to_addrs, body_text, attachment_files=[attachment_file])
