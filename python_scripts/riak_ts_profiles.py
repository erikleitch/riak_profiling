#!/usr/bin/python

from riak_graphviz import Node, DiGraph
from riak_graphviz import getTimeStr

face="verdana"

def getLegend():
    tag = '&nbsp;'
    tag += ':<FONT face="' + face + '" color="red">&mdash;  gen_fsm behaviour</FONT>'
    tag += ':<FONT color="cyan">&mdash; gen_server behaviour</FONT>'
    tag += ':<FONT color="purple">&mdash; internode link</FONT>'
    tag += ':<FONT color="black">&diams; multiple connections</FONT>'

    legend = Node({'label': 'Legend',       'color': 'black', 'annotation':tag})
    legend.setNodeAttr('Legend', 'shape', 'rectangle')
    return legend

def addAaeNodes(test):
    
    service_color = 'blue'
    fsm_color     = 'red'
    server_color  = 'cyan'
    internode_color = 'purple'

    riak_core_vnode = Node({'label':'riak_core_vnode', 'color':server_color})
    riak_core_vnode.append(
        (
            {'label':'riak_core_vnode:init'},
            {'label':'riak_kv_vnode:init'},
            {'label':'riak_kv_vnode:maybe_create_hashtrees'},
            {'label':'riak_kv_index_hashtree:start'},
            {'label':'gen_server:start'}
        )
    )

    riak_index_hash = Node({'label':'riak_kv_index_hashtree', 'color':server_color})
    riak_index_hash.append(
        (
            [
                (
                    {'label':'riak_kv_index_hashtree:init'},
                    [
                        (
                            {'label':'riak_kv_index_hashtree:reponsible_preflists'},
                            {'label':'riak_kv_util:reponsible_preflists', 'annotation':'determines preflist responsible:for this ring partition', 'annotationcolor':'darkgreen'},
                        ),
                        (
                            {'label':'riak_kv_index_hashtree:init_trees'},
                            {'label':'lists:foldl', 'tag':'foldl1'},
                            {'label':'riak_kv_index_hashtree:do_new_tree', 'annotation':'iterates over preflists:writing a tree to disk:for each node:in the preflist', 'annotationcolor':'darkgreen'},
                        )
                    ]
                ),
                (
                    {'label':'riak_kv_index_hashtree:handle_cast'},
                    {'label':'riak_kv_index_hashtree:do_poke'},
                    [
                        {'label':'riak_kv_index_hashtree:maybe_expire'},
                        (
                            {'label':'riak_kv_index_hashtree:maybe_rebuild'},
                            {'label':'erlang:spawn_link'},
                            {'label':'riak_kv_index_hashtree:build_or_rehash'},
                            {'label':'riak_kv_index_hashtree:fold_keys'},
                            {'label':'riak_core_vnode_master:sync_command'},
                            {'label':'gen_server:call'},
                        ),
                        {'label':'riak_kv_index_hashtree:maybe_build'},
                    ]
                )
            ]
        )
    )
    
    riak_em = Node({'label':'riak_kv_entropy_manager', 'color':server_color})
    riak_em.append(
        (
            [
                (
                    {'label':'riak_kv_entropy_manager:init'},
                    {'label':'riak_kv_entropy_manager:schedule_tick', 'annotation':'schedules a 15-second tick', 'annotationcolor':'darkgreen'},
                ),
                (
                    {'label':'riak_kv_entropy_manager:tick'},
                    [
                        {'label':'riak_kv_entropy_manager:maybe_reload_hashtrees'},
                        (
                            {'label':'lists:foldl', 'tag':'foldl2'},
                            {'label':'riak_kv_entropy_manager:maybe_poke_tree'},
                            {'label':'riak_kv_index_hashtree:poke'},
                            {'label':'gen_server:cast'},
                        ),
                        {'label':'riak_kv_entropy_manager:maybe_exchange'},
                    ]
                )
            ]
        )
    )

    test.append(riak_core_vnode)
    test.append(riak_index_hash)
    test.append(riak_em)

    test.edge('gen_server:start','riak_kv_index_hashtree:init', {'label':'1', 'color':server_color})
    test.edge('gen_server:cast','riak_kv_index_hashtree:handle_cast', {'label':'2', 'color':server_color})
    
def addTsListKeysNodes(test):
    
    service_color = 'blue'
    fsm_color     = 'red'
    server_color  = 'cyan'
    internode_color = 'purple'

    #------------------------------------------------------------
    # User process
    #------------------------------------------------------------
        
    riakc = Node({'label': 'user process',       'color': service_color})

    riakc.append(
        [
            (
                {'label': 'riakc:streaming_list_keys'},
                {'label': 'riakc:server_call'},
                {'tag':'gen_server_call1', 'label': 'gen_server:call'}
            ),
            {'label': 'receive', 'tag':'receive1'},
        ]
    )

    #------------------------------------------------------------
    # riak_pc_socket
    #------------------------------------------------------------

    riakpb = Node({'label': 'riakc_pb_socket',       'color': server_color})

    riakpb.append(
        [
            (
                {'label': 'riakc_pb_socket:handle_call'},
                {'label': 'riakc_pb_socket:send_request'},
                [
                    {'label': 'riakc_pb_socket:encode_request_message', 'annotation':'request encoded:(T2PB | T2B)'},
                    {'label': 'gen_tcp:send'}
                ]
            )
        ]
    )

    riakpb.setNodeAttr('riakc_pb_socket', 'rank', 'same')

    #------------------------------------------------------------
    # riak_api_pb_server
    #------------------------------------------------------------

    riakapi = Node({'label': 'riak_api_pb_server',       'color': fsm_color})

    riakapi.append(
        [
            (
                {'label': 'riak_api_pb_server:connected'},
                [
                    {'label': 'riak_kv_ts_svc:decode', 'annotation':'request decoded:(PB2T | B2T)'},
                    {'label': 'riak_api_pb_server:process_message'},
                ],
                [
                    (
                        {'label': 'riak_kv_ts_svc:process'},
                        {'label': 'riak_kv_ts_svc:check_table_and_call'},
                        [
                            (
                                {'label': 'riak_kv_ts_svc:sub_tslistkeysreq'},
                                {'label': 'riak_client:stream_list_keys'},
                                {'label': 'riak_kv_keys_fsm_sup:start_keys_fsm'},
                                {'label': 'supervisor:start_child'}
                            ),
                        ],
                    ),
                ]
            ),
            (
                {'label': 'riak_api_pb_server:process_stream', 'tag': 'riak_api_pb_server_process_stream1',
                 'annotation':'sext:decode on keys'},
                {'label': 'riak_api_pb_server:send_encoded_message_or_error'},
                {'label': 'riak_pb_codec:encode', 'annotation':'response encoded:(T2PB | T2B)'},
                {'label': 'riak_api_pb_server:send_message'},
            )
        ]
    )

    riakapi.setNodeAttr('riak_api_pb_server', 'rank', 'same')

    #------------------------------------------------------------
    # riak_kv_keys_fsm
    #------------------------------------------------------------

    riak_kv_keys_fsm = Node({'label':'riak_kv_keys_fsm', 'color':fsm_color})
    riak_kv_keys_fsm.setNodeAttr('riak_kv_keys_fsm', 'rank', 'same')

    riak_kv_keys_fsm.append(
        [
            (
                {'label':'riak_core_coverage_fsm:init'},
                [
                    {'label':'riak_kv_keys_fsm:init'},
                    (
                        {'label':'riak_core_coverage_fsm:initialize'},
                        {'label':'riak_core_vnode_master:coverage'},
                        {'tag':'gen_server_cast1', 'label':'gen_server:cast'},
                    )
                ]
            ),
            (
                {'label':'riak_core_coverage_fsm:waiting_results', 'tag':'riak_core_coverage_fsm_waiting_results1'},
                {'label':'riak_kv_keys_fsm:process_results'},
                [
                    {'label':'riak_kv_keys_fsm:process_keys'},
                    {'label':'riak_kv_vnode:ack_keys'},
                ]
            ),
            (
                {'label':'riak_core_coverage_fsm:waiting_results', 'tag':'riak_core_coverage_fsm_waiting_results2'},
                {'label':'riak_kv_keys_fsm:finish'},
            )

        ]
    )

    #------------------------------------------------------------
    # riak_core_vnode
    #------------------------------------------------------------

    riak_core_vnode = Node({'label':'riak_core_vnode', 'color':fsm_color})
    riak_core_vnode.setNodeAttr('riak_core_vnode', 'rank', 'same')
    riak_core_vnode.append(
        (
            {'label':'riak_core_vnode:active'},
            [
                (
                    {'label':'riak_core_vnode:vnode_coverage'},
                    {'label':'riak_kv_vnode:handle_coverage'},
                    {'label':'riak_kv_vnode:handle_coverage_keyfold'},
                    (
                        {'label':'riak_kv_vnode:handle_coverage_fold'},
                        {'label':'riak_kv_coverage_filter:build_filter'},
                    )
                ),
                (
                    {'label':'riak_core_vnode_worker_pool:handle_work'},
                    {'label':'gen_fsm:send_event'},
                )
            ]
        )
    )

    #------------------------------------------------------------
    # riak_core_vnode_worker
    #------------------------------------------------------------

    riak_cvw = Node({'label':'riak_core_vnode_worker', 'color':server_color})
    riak_cvw.setNodeAttr('riak_core_vnode_worker', 'rank', 'same')
    riak_cvw.append(
        (
            {'label':'riak_core_vnode_worker:handle_cast'},
            {'label':'riak_core_vnode_worker:handle_work'},
            {'label':'riak_kv_worker:handle_work'},
            [
                (
                    {'label':'eleveldb:fold_keys'},
                    {'label':'eleveldb:fold_loop'},
                    (
                        {'label':'riak_kv_eleveldb_backend:fold_keys_fun',
                         'annotation':'if filter was built:in handle_coverage_fold:only add to buffer:if key passes the filter','annotationcolor':'gray'},
                        [
                            {'label':'riak_kv_eleveldb_backend:from_object_key', 'annotation':'Object key decoded'},
                            (
                                {'label':'riak_kv_fold_buffer:add'},
                                (
                                    {'label':'riak_kv_vnode:result_fun_ack'},
                                    [
                                        {'label':'riak_core_vnode:reply', 'tag':'riak_core_vnode_reply1'},
                                        {'label':'receive', 'tag':'receive2'},
                                    ]
                                )
                            )
                        ]
                    )
                ),
                (
                    {'label':'riak_kv_vnode:finish_fold'},
                    {'label':'riak_core_vnode:reply', 'tag':'riak_core_vnode_reply2'},
                )
            ]
        )
    )
    
    test.append(riakc)
    test.append(riakpb)
    test.append(riakapi)
    test.append(riak_kv_keys_fsm)
    test.append(riak_core_vnode)
    test.append(riak_cvw)
    test.append(getLegend())

    test.edge('gen_server_call1',      'riakc_pb_socket:handle_call',  {'label':'1', 'color':server_color})

    test.edge('gen_tcp:send',          'riak_api_pb_server:connected', {'label':'2', 'color':fsm_color})

    test.edge('supervisor:start_child','riak_core_coverage_fsm:init',  {'label':'3', 'color':server_color})

    test.edge('gen_server_cast1',      'riak_core_vnode:active',       {'label':'4', 'color':internode_color, 'arrowhead':'diamond'})

    test.edge('gen_fsm:send_event',    'riak_core_vnode_worker:handle_cast',  {'label':'5', 'color':server_color})

    test.edge('riak_core_vnode_reply1', 'riak_core_coverage_fsm_waiting_results1',  {'label':'6', 'color':internode_color, 'arrowhead':'diamond'})

    test.edge('riak_kv_keys_fsm:process_keys', 'riak_api_pb_server_process_stream1', {'label':'7', 'color':server_color})

    test.edge('riak_api_pb_server:send_message', 'receive1', {'label':' ', 'color':server_color})
    
    test.edge('riak_kv_vnode:ack_keys', 'receive2',  {'label':'8', 'color':internode_color, 'arrowhead':'diamond'})

    test.edge('riak_core_vnode_reply2', 'riak_core_coverage_fsm_waiting_results2',  {'label':'9', 'color':internode_color, 'arrowhead':'diamond'})

    test.edge('riak_kv_keys_fsm:finish', 'riak_api_pb_server_process_stream1', {'label':'10', 'color':server_color})


def addTs1_1PutNodes(test):
    
    service_color = 'blue'
    fsm_color     = 'red'
    server_color  = 'cyan'
    internode_color = 'purple'
    
    #------------------------------------------------------------
    # riakc
    #------------------------------------------------------------
        
    riakc = Node({'label': 'riakc',       'color': service_color})

    riakc.append(
        (
            {'label': 'riakc_ts:put'},
            [
                (
                    {'label': 'riakc_ts:server_call'},
                    {'tag':'gen_server_call1', 'label': 'gen_server:call'}
                ),
                {'label': 'riakc_ts_put_operator:deserialize'},
            ]
        )
    )

    #------------------------------------------------------------
    # riak_pc_socket
    #------------------------------------------------------------

    riakpb = Node({'label': 'riakc_pb_socket',       'color': server_color})

    riakpb.setNodeAttr('riakc_pb_socket', 'rank', 'same')
                       
    riakpb.append(
        [
            (
                {'label': 'riakc_pb_socket:handle_call'},
                {'label': 'riakc_pb_socket:send_request', 'tag':'pathtosend'},
                [
                    {'label': 'riakc_pb_socket:encode_request_message', 'annotation':'records encoded:(T2PB | T2B)'},
                    {'label': 'gen_tcp:send'}
                ]
            ),
            (
                {'label': 'riakc_pb_socket:handle_info'},
                [
                    {'label': 'riak_pb_codec:decode', 'annotation':'response decoded:(PB2T | B2T)', 'tag':'responsedecoded'},
                    (
                        {'label': 'riakc_pb_socket:send_caller'},
                        {'label' : 'gen_server:reply'}
                    )
                ]
            )
        ]
    )
    
    #------------------------------------------------------------
    # riak_api_pb_server
    #------------------------------------------------------------

    riakapi = Node({'label': 'riak_api_pb_server',       'color': fsm_color})

    riakapi.append(
        (
            {'label': 'riak_api_pb_server:connected'},
            [
                {'label': 'riak_kv_pb_timeseries:decode', 'annotation':'records decoded:(PB2T | B2T)'},
                {'label': 'riak_api_pb_server:process_message'},
            ],
            [
                (
                    {'label': 'riak_kv_pb_timeseries:process'},
                    {'label': 'riak_kv_pb_timeseries:process_tsreq'},
                    [
                        {'label': 'riak_ql_ddl:make_module_name'},
                        (
                            {'label': 'riak_kv_pb_timeseries:put_data','annotation':'calculates preflist','annotationcolor':'gray'},
                            [
                                {'label': 'Mod:get_ddl'},
                                {'label': 'partition_data'},
                                (
                                    {'label': 'lists:foldl', 'tag': 'putfold'},
                                    [
                                        {'label': 'riak_kv_w1c_worker:validate_options'},
                                        {'label': 'riak_kv_w1c_worker:build_object', 'annotation':'builds new Riak obj'},
                                        (
                                            {'label': 'riak_kv_w1c_worker:async_put'},
                                            [
                                                (
                                                    {'label': 'riak_object:to_binary', 'annotation':'converts:from Riak object:to binary:(custom binary with T2MSGPACK for value)'},
                                                    {'label': 'riak_object:encode'},
                                                ),
                                                {'label': 'gen_server:cast', 'tag':'gen_server_cast1'},
                                            ]
                                        )
                                    ]
                                ),
                                {'label': 'riak_kv_w1c_worker:async_put_replies'},
                            ]
                        ),
                    ],
                ),
                (
                    {'label': 'riak_api_pb_server:send_encoded_message_or_error'},
                    {'label': 'riak_pb_codec:encode', 'annotation':'response encoded:(T2PB | T2B)'},
                    {'label': 'riak_api_pb_server:send_message'},
                )
            ]
        )
    )

    #------------------------------------------------------------
    # riak_kv_w1c_worker
    #------------------------------------------------------------
    
    riakw1cworker = Node({'label': 'riak_kv_w1c_worker',       'color': server_color})

    riakw1cworker.append(
        (
            {'label': 'riak_kv_w1c_worker:handle_cast'},
            {'label': 'riak_kv_w1c_worker:send_vnodes'},
            {'label': 'gen_fsm:send_event'}
        )
    )

    #------------------------------------------------------------
    # riak_kv_vnode
    #------------------------------------------------------------
    
    riakcorevnode = Node({'label': 'riak_core_vnode',       'color': fsm_color})

    riakcorevnode.append(
        (
            {'label': 'riak_core_vnode:vnode_command'},
            [
                (
                    {'label': 'riak_kv_vnode:handle_command'},
                    {'label': 'riak_kv_eleveldb_backend:sync_put'},
                    [
                        {'label': 'riak_kv_eleveldb_backend:to_object_key'},
                        (
                            {'label': 'eleveldb:sync_put'},
                            {'label': 'eleveldb:sync_write'},
                        )
                    ]
                ),
                {'label': 'riak_core_vnode:reply'},
            ]
        )
    )

    test.append(riakc)
    test.append(riakpb)
    test.append(riakapi)
    test.append(riakw1cworker)
    test.append(riakcorevnode)
    test.append(getLegend())
    
    test.edge('gen_server_call1',               'riakc_pb_socket:handle_call',          {'label':'1', 'color':server_color})
    test.edge('gen_tcp:send',                   'riak_api_pb_server:connected',         {'label':'2', 'color':fsm_color})
    test.edge('gen_server_cast1',               'riak_kv_w1c_worker:handle_cast',       {'label':'3', 'color':server_color})
    test.edge('gen_fsm:send_event',             'riak_core_vnode:vnode_command',        {'label':'4', 'color':internode_color, 'arrowhead':'diamond'})
    test.edge('riak_core_vnode:reply',          'riak_kv_w1c_worker:async_put_replies', {'label':'5', 'color':internode_color, 'arrowhead':'diamond'})
    test.edge('riak_api_pb_server:send_message','riakc_pb_socket:handle_info',          {'label':'6', 'color':server_color})
    test.edge('gen_server:reply',               'gen_server_call1',                     {'label':'7', 'color':server_color})
    

def addTs1_3PutNodes(test):
    
    service_color = 'blue'
    fsm_color     = 'red'
    server_color  = 'cyan'
    internode_color = 'purple'
    
    #------------------------------------------------------------
    # riakc
    #------------------------------------------------------------
        
    riakc = Node({'label': 'riakc',       'color': service_color})

    riakc.append(
        (
            {'label': 'riakc_ts:put'},
            [
                (
                    {'label': 'riakc_ts:server_call'},
                    {'tag':'gen_server_call1', 'label': 'gen_server:call'}
                ),
                {'label': 'riakc_ts_put_operator:deserialize'},
            ]
        )
    )

    #------------------------------------------------------------
    # riak_pc_socket
    #------------------------------------------------------------

    riakpb = Node({'label': 'riakc_pb_socket',       'color': server_color})

    riakpb.setNodeAttr('riakc_pb_socket', 'rank', 'same')
                       
    riakpb.append(
        [
            (
                {'label': 'riakc_pb_socket:handle_call'},
                {'label': 'riakc_pb_socket:send_request', 'tag':'pathtosend'},
                [
                    {'label': 'riakc_pb_socket:encode_request_message', 'annotation':'records encoded:(T2PB | T2B)'},
                    {'label': 'gen_tcp:send'}
                ]
            ),
            (
                {'label': 'riakc_pb_socket:handle_info'},
                [
                    {'label': 'riak_pb_codec:decode', 'annotation':'response decoded:(PB2T | B2T)'},
                    (
                        {'label': 'riakc_pb_socket:send_caller'},
                        {'label' : 'gen_server:reply'}
                    )
                ]
            )
        ]
    )
    
    #------------------------------------------------------------
    # riak_api_pb_server
    #------------------------------------------------------------

    riakapi = Node({'label': 'riak_api_pb_server',       'color': fsm_color})

    riakapi.append(
        (
            {'label': 'riak_api_pb_server:connected'},
            [
                {'label': 'riak_kv_ttb_ts:decode', 'annotation':'records decoded:(PB2T | B2T)'},
                {'label': 'riak_api_pb_server:process_message'},
            ],
            [
                (
                    {'label': 'riak_kv_ts_svc:process'},
                    {'label': 'riak_kv_ts_svc:check_table_and_call'},
                    [
                        {'label': 'riak_kv_ts_util:get_table_ddl'},
                        (
                            {'label': 'riak_kv_ts_svc:sub_tsputreq'},
                            {'label': 'riak_kv_ts_api:put_data','annotation':'calculates preflist','annotationcolor':'gray'},
                            [
                                {'label': 'Mod:get_ddl'},
                                {'label': 'partition_data'},
                                (
                                    {'label': 'lists:foldl', 'tag': 'putfold'},
                                    [
                                        {'label': 'riak_kv_w1c_worker:validate_options'},
                                        {'label': 'riak_kv_ts_api:pick_batch_options', 'tag':'batchoptionsblock'},
                                        (
                                            {'label': 'riak_kv_ts_api:invoke_sync_put'},
                                            [
                                                {'label': 'riak_kv_ts_api:build_object', 'annotation':'builds new Riak obj'},
                                                (
                                                    {'label': 'riak_kv_w1c_worker:async_put'},
                                                    [
                                                        (
                                                            {'label': 'riak_object:to_binary', 'annotation':'converts:from Riak object:to binary:(custom binary with T2MSGPACK for value)'},
                                                            {'label': 'riak_object:encode'},
                                                        ),
                                                        {'label': 'gen_server:cast', 'tag':'gen_server_cast1'},
                                                    ]
                                                )
                                            ]
                                        )
                                    ]
                                ),
                                {'label': 'riak_kv_w1c_worker:async_put_replies'},
                            ]
                        ),
                    ],
                ),
                (
                    {'label': 'riak_api_pb_server:send_encoded_message_or_error'},
                    {'label': 'riak_pb_codec:encode', 'annotation':'response encoded:(T2PB | T2B)'},
                    {'label': 'riak_api_pb_server:send_message'},
                )
            ]
        )
    )

    #------------------------------------------------------------
    # riak_kv_w1c_worker
    #------------------------------------------------------------
    
    riakw1cworker = Node({'label': 'riak_kv_w1c_worker',       'color': server_color})

    riakw1cworker.append(
        (
            {'label': 'riak_kv_w1c_worker:handle_cast'},
            {'label': 'riak_kv_w1c_worker:send_vnodes'},
            {'label': 'gen_fsm:send_event'}
        )
    )

    #------------------------------------------------------------
    # riak_kv_vnode
    #------------------------------------------------------------
    
    riakcorevnode = Node({'label': 'riak_core_vnode',       'color': fsm_color})

    riakcorevnode.append(
        (
            {'label': 'riak_core_vnode:vnode_command'},
            [
                (
                    {'label': 'riak_kv_vnode:handle_command'},
                    {'label': 'riak_kv_eleveldb_backend:sync_put'},
                    [
                        {'label': 'riak_kv_eleveldb_backend:to_object_key'},
                        (
                            {'label': 'eleveldb:sync_put'},
                            {'label': 'eleveldb:sync_write'},
                        )
                    ]
                ),
                {'label': 'riak_core_vnode:reply'},
            ]
        )
    )

    test.append(riakc)
    test.append(riakpb)
    test.append(riakapi)
    test.append(riakw1cworker)
    test.append(riakcorevnode)
    test.append(getLegend())
    
    test.edge('gen_server_call1',               'riakc_pb_socket:handle_call',          {'label':'1', 'color':server_color})
    test.edge('gen_tcp:send',                   'riak_api_pb_server:connected',         {'label':'2', 'color':fsm_color})
    test.edge('gen_server_cast1',               'riak_kv_w1c_worker:handle_cast',       {'label':'3', 'color':server_color})
    test.edge('gen_fsm:send_event',             'riak_core_vnode:vnode_command',        {'label':'4', 'color':internode_color, 'arrowhead':'diamond'})
    test.edge('riak_core_vnode:reply',          'riak_kv_w1c_worker:async_put_replies', {'label':'5', 'color':internode_color, 'arrowhead':'diamond'})
    test.edge('riak_api_pb_server:send_message','riakc_pb_socket:handle_info',          {'label':'6', 'color':server_color})
    test.edge('gen_server:reply',               'gen_server_call1',                     {'label':'7', 'color':server_color})
    
def addGetNodes(test):
    
    service_color = 'blue'
    fsm_color     = 'red'
    server_color  = 'cyan'
    internode_color = 'purple'
    
    #------------------------------------------------------------
    # riakc
    #------------------------------------------------------------
        
    riakc = Node({'label': 'user process',       'color': service_color})

    riakc.append(
        (
            {'label': 'riakc_pb_socket:get'},
            {'tag':'gen_server_call1', 'label': 'gen_server:call', 'annotation':'(rpbgetreq)','annotationcolor':'gray'}
        )
    )

    #------------------------------------------------------------
    # riak_pc_socket
    #------------------------------------------------------------

    riakpb = Node({'label': 'riakc_pb_socket',       'color': server_color})

    riakpb.setNodeAttr('riakc_pb_socket', 'rank', 'same')
                       
    riakpb.append(
        [
            (
                {'label': 'riakc_pb_socket:handle_call'},
                {'label': 'riakc_pb_socket:send_request'},
                [
                    {'label': 'riakc_pb_socket:encode_request_message', 'annotation':'request encoded:(T2PB | T2B)'},
                    {'label': 'gen_tcp:send'}
                ]
            ),
            (
                {'label': 'riakc_pb_socket:handle_info'},
                [
                    {'label': 'riak_pb_codec:decode', 'annotation':'response decoded:(PB2T | B2T)'},
                    (
                        {'label': 'riakc_pb_socket:send_caller'},
                        {'label' : 'gen_server:reply'}
                    )
                ]
            )
        ]
    )
    
    #------------------------------------------------------------
    # riak_api_pb_server
    #------------------------------------------------------------

    riakapi = Node({'label': 'riak_api_pb_server',       'color': fsm_color})

    riakapi.append(
        (
            {'label': 'riak_api_pb_server:connected'},
            [
                {'label': 'riak_kv_pb_object:decode', 'annotation':'request decoded:(PB2T | B2T)'},
                {'label': 'riak_api_pb_server:process_message'},
            ],
            [
                (
                    {'label': 'riak_kv_pb_object:process', 'annotation':'builds rpbgetresp:with encoded contents:extracts and encodes vclock'},
                    [
                        {'label': 'riak_kv_pb_object:decode_quorum'},
                        (
                            {'label': 'riak_client:get'},
                            {'label': 'riak_client:normal_get'},
                            [
                                {'label': 'riak_kv_get_fsm:start_link'},
                                {'label': 'riak_client:wait_for_reqid'},
                            ]
                        ),
                        {'label': 'riak_object:get_contents'},
                        {'label': 'riak_pb_kv_codec:encode_contents', 'annotation':'converts:from Riak Obj:to binary (T2B)'},
                    ]
                ),
                (
                    {'label': 'riak_api_pb_server:send_encoded_message_or_error'},
                    {'label': 'riak_pb_codec:encode', 'annotation':'response encoded:(T2PB | T2B)'},
                    {'label': 'riak_api_pb_server:send_message'},
                )
            ]
        )
    )

    riakkvgetfsm = Node({'label': 'riak_kv_get_fsm',       'color': fsm_color})
    riakkvgetfsm.append(
        (
            [
                (
                    {'label': 'riak_kv_get_fsm:init'},
                    {'label': 'riak_kv_get_fsm:prepare', 'annotation':'(also computes preflist for get)', 'annotationcolor':'gray'},
                    (
                        {'label': 'riak_kv_get_fsm:validate'},
                        {'label': 'riak_kv_get_core:init'},
                    )
                ),
                (
                    {'label': 'riak_kv_get_fsm:execute'},
                    [
                        (
                            {'label': 'riak_kv_vnode:get'},
                            {'label': 'gen_fsm:send_event', 'tag':'gen_fsm_send_event1'},
                        ),
                        (
                            {'label': 'riak_kv_get_fsm:waiting_vnode_r'},
                            (
                                [
                                    (
                                        {'label': 'riak_kv_get_core:add_result'},
                                        {'label': 'riak_kv_util:is_x_deleted', 'annotation':'inspects object contents:for "X-Riak-Deleted"'},
                                    ),
                                    {'label': 'riak_kv_get_core:response', 'annotation':'merges objects'},
                                    {'label': 'riak_kv_get_fsm:finalize', 'annotation':'optionally initiates:read_repair or delete', 'annotationcolor':'gray'},
                                    {'label': 'riak_kv_get_fsm:client_reply'},
                                ]
                            ),

                        )
                    ]
                )
            ]
        )
    )
    
    #------------------------------------------------------------
    # riak_kv_vnode
    #------------------------------------------------------------
    
    riakcorevnode = Node({'label': 'riak_core_vnode',       'color': fsm_color})

    riakcorevnode.append(
        (
            {'label': 'riak_core_vnode:vnode_command'},
            [
                (
                    {'label': 'riak_kv_vnode:handle_command'},
                    {'label': 'riak_kv_vnode:do_get'},
                    [
                        (
                            {'label': 'riak_kv_vnode:do_get_term'},
                            {'label': 'riak_kv_vnode:do_get_object'},
                            [
                                (
                                    {'label': 'riak_kv_vnode:do_get_binary'},
                                    {'label': 'riak_kv_eleveldb_backend:get'},
                                    {'label': 'eleveldb:get'},
                                ),
                                {'label': 'riak_object:from_binary', 'annotation':'converts:from binary:to Riak obj '},
                            ]
                        ),
                        {'label': 'riak_kv_vnode:maybe_cache_object'},
                    ]
                ),
                {'label': 'riak_core_vnode:reply', 'tag':'reply2'},
            ]
        )
    )

    test.append(riakc)
    test.append(riakpb)
    test.append(riakapi)
    test.append(riakkvgetfsm)
    test.append(riakcorevnode)
    test.append(getLegend())
    
    if True:
        test.edge('gen_server_call1',               'riakc_pb_socket:handle_call',          {'label':'1', 'color':server_color})
        test.edge('gen_tcp:send',                   'riak_api_pb_server:connected',         {'label':'2', 'color':fsm_color})
        test.edge('riak_kv_get_fsm:start_link',     'riak_kv_get_fsm:init',                 {'label':'3', 'color':fsm_color})
        test.edge('gen_fsm_send_event1',            'riak_core_vnode:vnode_command',        {'label':'4', 'color':internode_color,'arrowhead':'diamond'})
        test.edge('reply2',                 'riak_kv_get_fsm:waiting_vnode_r',         {'label':'5', 'color':internode_color,'arrowhead':'diamond'})
                
        test.edge('riak_kv_get_fsm:client_reply',    'riak_client:wait_for_reqid',          {'label':'6', 'color':fsm_color})
        test.edge('riak_api_pb_server:send_message','riakc_pb_socket:handle_info',          {'label':'7', 'color':server_color})
        test.edge('gen_server:reply',               'gen_server_call1',                     {'label':'8', 'color':server_color})

def addPutNodes(test):
    
    service_color = 'blue'
    fsm_color     = 'red'
    server_color  = 'cyan'
    internode_color = 'purple'
    
    #------------------------------------------------------------
    # riakc
    #------------------------------------------------------------
        
    riakc = Node({'label': 'user process',       'color': service_color})

    riakc.append(
        (
            [
                {'tag':'new1', 'label': 'riak_object:new', 'annotation':'Creates new Riak obj:from key/val'},
                (
                    {'label': 'riakc_pb_socket:put'},
                    [
                        {'label': 'riak_pb_kv_codec:encode_content', 'annotation':'extracts metadata and value from object:optionally encodes value to binary (T2B):and updates metadata'},
                        {'tag':'gen_server_call1', 'label': 'gen_server:call', 'annotation':'(rpbputreq)','annotationcolor':'gray'}
                    ]
                )
            ]
        )
    )

    #------------------------------------------------------------
    # riak_pc_socket
    #------------------------------------------------------------

    riakpb = Node({'label': 'riakc_pb_socket',       'color': server_color})

    riakpb.setNodeAttr('riakc_pb_socket', 'rank', 'same')
                       
    riakpb.append(
        [
            (
                {'label': 'riakc_pb_socket:handle_call'},
                {'label': 'riakc_pb_socket:send_request'},
                [
                    {'label': 'riakc_pb_socket:encode_request_message', 'annotation':'request encoded:(T2PB | T2B)'},
                    {'label': 'gen_tcp:send'}
                ]
            ),
            (
                {'label': 'riakc_pb_socket:handle_info'},
                [
                    {'label': 'riak_pb_codec:decode', 'annotation':'response decoded:(PB2T | B2T)'},
                    (
                        {'label': 'riakc_pb_socket:send_caller'},
                        {'label' : 'gen_server:reply'}
                    )
                ]
            )
        ]
    )
    
    #------------------------------------------------------------
    # riak_api_pb_server
    #------------------------------------------------------------

    riakapi = Node({'label': 'riak_api_pb_server',       'color': fsm_color})

    riakapi.append(
        (
            {'label': 'riak_api_pb_server:connected'},
            [
                {'label': 'riak_kv_pb_object:decode', 'annotation':'request decoded:(PB2T | B2T)'},
                {'label': 'riak_api_pb_server:process_message'},
            ],
            [
                (
                    {'label': 'riak_kv_pb_object:process'},
                    [
                        {'label': 'riak_object:new', 'annotation':'Creates new Riak obj:from request container'},
                        (
                            {'label': 'riak_kv_pb_object:update_rpb_content'},
                            {'label': 'riak_pb_kv_codec:decode_content', 'annotation':'decodes object contents:(B2T)'},
                        ),
                        {'label': 'riak_kv_pb_object:decode_quorum'},
                        (
                            {'label': 'riak_client:put'},
                            {'label': 'riak_client:normal_put'},
                            [
                                {'label': 'riak_kv_put_fsm:start_link'},
                                {'label': 'riak_client:wait_for_reqid'},
                            ]
                        )
                    ]
                ),
                (
                    {'label': 'riak_api_pb_server:send_encoded_message_or_error'},
                    {'label': 'riak_pb_codec:encode', 'annotation':'response encoded:(T2PB | T2B)'},
                    {'label': 'riak_api_pb_server:send_message'},
                )
            ]
        )
    )

    riakkvputfsm = Node({'label': 'riak_kv_put_fsm',       'color': fsm_color})
    riakkvputfsm.append(
        (
            [
                (
                    {'label': 'riak_kv_put_fsm:init'},
                    {'label': 'riak_kv_put_fsm:prepare', 'annotation':'(also computes preflist for put)', 'annotationcolor':'gray'},
                    {'label': 'riak_kv_put_fsm:validate'},
                ),
                (
                    {'label': 'riak_kv_put_fsm:execute_local'},
                    [
                        (
                            {'label': 'riak_kv_vnode:coord_put'},
                            {'label': 'gen_fsm:send_event', 'tag':'gen_fsm_send_event1'},
                        ),
                        {'label': 'riak_kv_put_fsm:waiting_local_vnode'}
                    ]
                ),
                (
                    {'label': 'riak_kv_put_fsm:execute_remote'},
                    [
                        (
                            {'label': 'riak_kv_vnode:put'},
                            {'label': 'gen_fsm:send_event', 'tag':'gen_fsm_send_event2'},
                        ),
                        (
                            {'label': 'riak_kv_put_fsm:waiting_remote_vnode'},
                            {'label': 'riak_kv_put_fsm:client_reply'},
                        )
                    ]
                )
            ]
        )
    )
    
    #------------------------------------------------------------
    # riak_kv_vnode
    #------------------------------------------------------------
    
    riakcorevnode = Node({'label': 'riak_core_vnode',       'color': fsm_color})

    riakcorevnode.append(
        (
            {'label': 'riak_core_vnode:vnode_command'},
            [
                (
                    {'label': 'riak_kv_vnode:handle_command'},
                    [
                        {'label': 'riak_core_vnode:reply', 'tag':'reply1'},
                        (
                            {'label': 'riak_kv_vnode:do_put'},
                            [
                                {'label': 'riak_kv_vnode:prepare_put', 'annotation':'optionally increments vclock:performs local get if necessary:(if index bucket, or not last-write-wins)'},
                                (
                                    {'label': 'riak_kv_vnode:perform_put'},
                                    {'label': 'riak_kv_vnode:encode_and_put','annotation':'counts siblings'},
                                    [
                                        (
                                            {'label': 'riak_object:to_binary', 'annotation':'converts:from Riak object:to binary:(custom binary with T2B for value)'},
                                            {'label': 'riak_kv_eleveldb_backend:put'},
                                        )
                                    ]
                                ),
                                {'label': 'riak_core_vnode:reply', 'tag':'reply2'},
                            ]
                        )
                    ]
                )
            ]
        )
    )

    riakcorevnode.setNodeAttr('riak_kv_vnode:encode_and_put','rank', 'same')
    
    test.append(riakc)
    test.append(riakpb)
    test.append(riakapi)
    test.append(riakkvputfsm)
    test.append(riakcorevnode)
    test.append(getLegend())
    
    if True:
        test.edge('gen_server_call1',               'riakc_pb_socket:handle_call',          {'label':'1', 'color':server_color})
        test.edge('gen_tcp:send',                   'riak_api_pb_server:connected',         {'label':'2', 'color':fsm_color})
        test.edge('riak_kv_put_fsm:start_link',     'riak_kv_put_fsm:init',                 {'label':'3', 'color':fsm_color})
        test.edge('gen_fsm_send_event1',            'riak_core_vnode:vnode_command',        {'label':'4', 'color':fsm_color})

        test.edge('reply1',                 'riak_kv_put_fsm:waiting_local_vnode',          {'label':'5', 'color':fsm_color})
        test.edge('reply2',                 'riak_kv_put_fsm:waiting_local_vnode',          {'label':'6', 'color':fsm_color})

        test.edge('gen_fsm_send_event2',            'riak_core_vnode:vnode_command',        {'label':'7', 'color':internode_color,'arrowhead':'diamond'})
        test.edge('reply2',                 'riak_kv_put_fsm:waiting_remote_vnode',         {'label':'8', 'color':internode_color,'arrowhead':'diamond'})
                
        test.edge('riak_kv_put_fsm:client_reply',    'riak_client:wait_for_reqid',          {'label':'9', 'color':fsm_color})
        test.edge('riak_api_pb_server:send_message','riakc_pb_socket:handle_info',          {'label':'10', 'color':server_color})
        test.edge('gen_server:reply',               'gen_server_call1',                     {'label':'11', 'color':server_color})

def addReadRepairNodes(test):
    
    service_color = 'blue'
    fsm_color     = 'red'
    server_color  = 'cyan'
    internode_color = 'purple'
    
    #------------------------------------------------------------
    # riakc
    #------------------------------------------------------------
        
    riakc = Node({'label': 'user process',       'color': service_color})

    riakc.append(
        (
            [
                {'tag':'new1', 'label': 'riak_object:new', 'annotation':'Creates new Riak obj:from key/val'},
                (
                    {'label': 'riakc_pb_socket:put'},
                    [
                        {'label': 'riak_pb_kv_codec:encode_content', 'annotation':'extracts metadata and value from object:optionally encodes value to binary (T2B):and updates metadata'},
                        {'tag':'gen_server_call1', 'label': 'gen_server:call', 'annotation':'(rpbputreq)','annotationcolor':'gray'}
                    ]
                )
            ]
        )
    )

    #------------------------------------------------------------
    # riak_pc_socket
    #------------------------------------------------------------

    riakpb = Node({'label': 'riakc_pb_socket',       'color': server_color})

    riakpb.setNodeAttr('riakc_pb_socket', 'rank', 'same')
                       
    riakpb.append(
        [
            (
                {'label': 'riakc_pb_socket:handle_call'},
                {'label': 'riakc_pb_socket:send_request'},
                [
                    {'label': 'riakc_pb_socket:encode_request_message', 'annotation':'request encoded:(T2PB | T2B)'},
                    {'label': 'gen_tcp:send'}
                ]
            ),
            (
                {'label': 'riakc_pb_socket:handle_info'},
                [
                    {'label': 'riak_pb_codec:decode', 'annotation':'response decoded:(PB2T | B2T)'},
                    (
                        {'label': 'riakc_pb_socket:send_caller'},
                        {'label' : 'gen_server:reply'}
                    )
                ]
            )
        ]
    )
    
    #------------------------------------------------------------
    # riak_api_pb_server
    #------------------------------------------------------------

    riakapi = Node({'label': 'riak_api_pb_server',       'color': fsm_color})

    riakapi.append(
        (
            {'label': 'riak_api_pb_server:connected'},
            [
                {'label': 'riak_kv_pb_object:decode', 'annotation':'request decoded:(PB2T | B2T)'},
                {'label': 'riak_api_pb_server:process_message'},
            ],
            [
                (
                    {'label': 'riak_kv_pb_object:process'},
                    [
                        {'label': 'riak_object:new', 'annotation':'Creates new Riak obj:from request container'},
                        (
                            {'label': 'riak_kv_pb_object:update_rpb_content'},
                            {'label': 'riak_pb_kv_codec:decode_content', 'annotation':'decodes object contents:(B2T)'},
                        ),
                        {'label': 'riak_kv_pb_object:decode_quorum'},
                        (
                            {'label': 'riak_client:put'},
                            {'label': 'riak_client:normal_put'},
                            [
                                {'label': 'riak_kv_put_fsm:start_link'},
                                {'label': 'riak_client:wait_for_reqid'},
                            ]
                        )
                    ]
                ),
                (
                    {'label': 'riak_api_pb_server:send_encoded_message_or_error'},
                    {'label': 'riak_pb_codec:encode', 'annotation':'response encoded:(T2PB | T2B)'},
                    {'label': 'riak_api_pb_server:send_message'},
                )
            ]
        )
    )

    riakkvputfsm = Node({'label': 'riak_kv_put_fsm',       'color': fsm_color})
    riakkvputfsm.append(
        (
            [
                (
                    {'label': 'riak_kv_put_fsm:init'},
                    {'label': 'riak_kv_put_fsm:prepare', 'annotation':'(also computes preflist for put)', 'annotationcolor':'gray'},
                    {'label': 'riak_kv_put_fsm:validate'},
                ),
                (
                    {'label': 'riak_kv_put_fsm:execute_local'},
                    [
                        (
                            {'label': 'riak_kv_vnode:coord_put'},
                            {'label': 'gen_fsm:send_event', 'tag':'gen_fsm_send_event1'},
                        ),
                        {'label': 'riak_kv_put_fsm:waiting_local_vnode'}
                    ]
                ),
                (
                    {'label': 'riak_kv_put_fsm:execute_remote'},
                    [
                        (
                            {'label': 'riak_kv_vnode:put'},
                            {'label': 'gen_fsm:send_event', 'tag':'gen_fsm_send_event2'},
                        ),
                        (
                            {'label': 'riak_kv_put_fsm:waiting_remote_vnode'},
                            {'label': 'riak_kv_put_fsm:client_reply'},
                        )
                    ]
                )
            ]
        )
    )
    
    #------------------------------------------------------------
    # riak_kv_vnode
    #------------------------------------------------------------
    
    riakcorevnode = Node({'label': 'riak_core_vnode',       'color': fsm_color})

    riakcorevnode.append(
        (
            {'label': 'riak_core_vnode:vnode_command'},
            [
                (
                    {'label': 'riak_kv_vnode:handle_command'},
                    [
                        {'label': 'riak_core_vnode:reply', 'tag':'reply1'},
                        (
                            {'label': 'riak_kv_vnode:do_put'},
                            [
                                {'label': 'riak_kv_vnode:prepare_put', 'annotation':'optionally increments vclock:performs local get if necessary:(if index bucket, or not last-write-wins)'},
                                (
                                    {'label': 'riak_kv_vnode:perform_put'},
                                    {'label': 'riak_kv_vnode:encode_and_put','annotation':'counts siblings'},
                                    [
                                        (
                                            {'label': 'riak_object:to_binary', 'annotation':'converts:from Riak object:to binary:(custom binary with T2B for value)'},
                                            {'label': 'riak_kv_eleveldb_backend:put'},
                                        )
                                    ]
                                ),
                                {'label': 'riak_core_vnode:reply', 'tag':'reply2'},
                            ]
                        )
                    ]
                )
            ]
        )
    )

    riakcorevnode.setNodeAttr('riak_kv_vnode:encode_and_put','rank', 'same')


    riakc.grayOut()
    riakpb.grayOut()
    riakapi.grayOut()
    riakkvputfsm.findNode('riak_kv_put_fsm:init').grayOut()
    riakkvputfsm.findNode('riak_kv_put_fsm:execute_local').grayOut()
    riakkvputfsm.findNode('riak_kv_put_fsm:client_reply').grayOut()
    riakkvputfsm.findNode('riak_kv_put_fsm:waiting_remote_vnode').grayOut()
    riakcorevnode.findNode('reply1').grayOut()
    
    test.append(riakc)
    test.append(riakpb)
    test.append(riakapi)
    test.append(riakkvputfsm)
    test.append(riakcorevnode)
    test.append(getLegend())


    
    if True:
        test.edge('gen_server_call1',               'riakc_pb_socket:handle_call',          {'label':'1', 'color':server_color})
        test.edge('gen_tcp:send',                   'riak_api_pb_server:connected',         {'label':'2', 'color':fsm_color})
        test.edge('riak_kv_put_fsm:start_link',     'riak_kv_put_fsm:init',                 {'label':'3', 'color':fsm_color})
        test.edge('gen_fsm_send_event1',            'riak_core_vnode:vnode_command',        {'label':'4', 'color':fsm_color})

        test.edge('reply1',                 'riak_kv_put_fsm:waiting_local_vnode',          {'label':'5', 'color':fsm_color})
        test.edge('reply2',                 'riak_kv_put_fsm:waiting_local_vnode',          {'label':'6', 'color':fsm_color})

        test.edge('gen_fsm_send_event2',            'riak_core_vnode:vnode_command',        {'label':'7', 'color':internode_color,'arrowhead':'diamond'})
        test.edge('reply2',                 'riak_kv_put_fsm:waiting_remote_vnode',         {'label':'8', 'color':internode_color,'arrowhead':'diamond'})
                
        test.edge('riak_kv_put_fsm:client_reply',    'riak_client:wait_for_reqid',          {'label':'9', 'color':fsm_color})
        test.edge('riak_api_pb_server:send_message','riakc_pb_socket:handle_info',          {'label':'10', 'color':server_color})
        test.edge('gen_server:reply',               'gen_server_call1',                     {'label':'11', 'color':server_color})
    
def addW1cPutNodes(test):
    
    service_color = 'blue'
    fsm_color     = 'red'
    server_color  = 'cyan'
    internode_color = 'purple'

    #------------------------------------------------------------
    # riakc
    #------------------------------------------------------------
        
    riakc = Node({'label': 'user process',       'color': service_color})

    riakc.append(
        (
            [
                {'tag':'new1', 'label': 'riak_object:new', 'annotation':'Creates new Riak obj:from key/val'},
                (
                    {'label': 'riakc_pb_socket:put'},
                    [
                        {'label': 'riak_pb_kv_codec:encode_content', 'annotation':'extracts metadata and value from object:optionally encodes value to binary (T2B):and updates metadata'},
                        {'tag':'gen_server_call1', 'label': 'gen_server:call', 'annotation':'(rpbputreq)','annotationcolor':'gray'}
                    ]
                )
            ]
        )
    )

    #------------------------------------------------------------
    # riak_pc_socket
    #------------------------------------------------------------

    riakpb = Node({'label': 'riakc_pb_socket',       'color': server_color})

    riakpb.setNodeAttr('riakc_pb_socket', 'rank', 'same')
                       
    riakpb.append(
        [
            (
                {'label': 'riakc_pb_socket:handle_call'},
                {'label': 'riakc_pb_socket:send_request'},
                [
                    {'label': 'riakc_pb_socket:encode_request_message', 'annotation':'request encoded:(T2PB | T2B)'},
                    {'label': 'gen_tcp:send'}
                ]
            ),
            (
                {'label': 'riakc_pb_socket:handle_info'},
                [
                    {'label': 'riak_pb_codec:decode', 'annotation':'response decoded:(PB2T | B2T)'},
                    (
                        {'label': 'riakc_pb_socket:send_caller'},
                        {'label' : 'gen_server:reply'}
                    )
                ]
            )
        ]
    )
    
    #------------------------------------------------------------
    # riak_api_pb_server
    #------------------------------------------------------------

    riakapi = Node({'label': 'riak_api_pb_server',       'color': fsm_color})

    riakapi.append(
        (
            {'label': 'riak_api_pb_server:connected'},
            [
                {'label': 'riak_kv_pb_object:decode', 'annotation':'request decoded:(PB2T | B2T)'},
                {'label': 'riak_api_pb_server:process_message'},
            ],
            [
                (
                    {'label': 'riak_kv_pb_object:process'},
                    [
                        {'label': 'riak_object:new', 'annotation':'Creates new Riak obj:from request container'},
                        (
                            {'label': 'riak_kv_pb_object:update_rpb_content'},
                            {'label': 'riak_pb_kv_codec:decode_content', 'annotation':'decodes object contents:(B2T)'},
                        ),
                        {'label': 'riak_kv_pb_object:decode_quorum'},
                        (
                            {'label': 'riak_client:put'},
                            {'label': 'riak_client:write_once_put'},
                            {'label': 'riak_kv_w1c_worker:put', 'annotation':'calculates preflist', 'annotationcolor':'gray'},
                            [
                                (
                                    {'label': 'riak_kv_w1c_worker:async_put'},
                                    [
                                        {'label': 'riak_object:to_binary', 'annotation':'converts:from Riak object:to binary:(custom binary with T2B for value)'},
                                        {'label': 'gen_server:cast'},
                                    ]
                                ),
                                {'label': 'riak_kv_w1c_worker:wait_for_put_reply'}
                            ]
                        )
                    ]
                ),
                (
                    {'label': 'riak_api_pb_server:send_encoded_message_or_error'},
                    {'label': 'riak_pb_codec:encode', 'annotation':'response encoded:(T2PB | T2B)'},
                    {'label': 'riak_api_pb_server:send_message'},
                )
            ]
        )
    )

    riakw1cworker = Node({'label': 'riak_kv_w1c_worker',       'color': server_color})
    riakw1cworker.setNodeAttr('riak_kv_w1c_worker', 'rank', 'same')
    
    riakw1cworker.append(
        (
            [
                (
                    {'label': 'riak_kv_w1c_worker:handle_cast'},
                    {'label': 'riak_kv_w1c_worker:send_vnodes'},
                    {'label': 'gen_fsm:send_event'},
                ),
                (
                    {'label': 'riak_kv_w1c_worker:handle_info'},
                    {'label': 'riak_kv_w1c_worker:reply'},
                )
            ]
        )
    )
    #------------------------------------------------------------
    # riak_kv_vnode
    #------------------------------------------------------------
    
    riakcorevnode = Node({'label': 'riak_core_vnode',       'color': fsm_color})

    riakcorevnode.append(
        (
            {'label': 'riak_core_vnode:vnode_command'},
            [
                (
                    {'label': 'riak_kv_vnode:handle_command'},
                    {'label': 'riak_kv_eleveldb_backend:sync_put'},
                    [
                        {'label': 'riak_kv_eleveldb_backend:to_object_key'},
                        (
                            {'label': 'eleveldb:sync_put'},
                            {'label': 'eleveldb:sync_write'},
                        )
                    ]
                ),
                {'label': 'riak_core_vnode:reply'},
            ]
        )
    )

    test.append(riakc)
    test.append(riakpb)
    test.append(riakapi)
    test.append(riakw1cworker)
    test.append(riakcorevnode)
    test.append(getLegend())
    
    test.edge('gen_server_call1',                'riakc_pb_socket:handle_call',          {'label':'1', 'color':server_color})
    test.edge('gen_tcp:send',                    'riak_api_pb_server:connected',         {'label':'2', 'color':fsm_color})
    test.edge('gen_server:cast',                 'riak_kv_w1c_worker:handle_cast',        {'label':'3', 'color':server_color})

    test.edge('gen_fsm:send_event',              'riak_core_vnode:vnode_command',        {'label':'4', 'color':internode_color, 'arrowhead':'diamond'})

    test.edge('riak_core_vnode:reply',           'riak_kv_w1c_worker:handle_info',       {'label':'5', 'color':internode_color, 'arrowhead':'diamond'})
    test.edge('riak_kv_w1c_worker:reply',        'riak_kv_w1c_worker:wait_for_put_reply',{'label':'6', 'color':server_color})
    test.edge('riak_api_pb_server:send_message', 'riakc_pb_socket:handle_info',          {'label':'7', 'color':server_color})
    test.edge('gen_server_reply',                'gen_server_call1',                     {'label':'8', 'color':server_color})
    
def addTsQueryNodes(test):
    
    service_color = 'blue'
    fsm_color     = 'red'
    server_color  = 'cyan'
    internode_color = 'purple'
    
    #------------------------------------------------------------
    # riakc
    #------------------------------------------------------------
        
    riakc = Node({'label': 'user process',       'color': service_color})

    riakc.append(({'label': 'riakc:query'},
                  {'label': 'riakc:server_call'},
                  {'tag':'gen_server_call1', 'label': 'gen_server:call'}))

    #------------------------------------------------------------
    # riak_pc_socket
    #------------------------------------------------------------

    riakpb = Node({'label': 'riakc_pb_socket',       'color': server_color})

    riakpb.setNodeAttr('riakc_pb_socket', 'rank', 'same')
                       
    riakpb.append(
        [
            (
                {'label': 'riakc_pb_socket:handle_call'},
                {'label': 'riakc_pb_socket:send_request'},
                [
                    {'label': 'riakc_pb_socket:encode_request_message', 'annotation':'request encoded:(T2PB | T2B)'},
                    {'label': 'gen_tcp:send'}
                ]
            ),
            (
                {'label': 'riakc_pb_socket:handle_info'},
                [
                    {'label': 'riak_pb_codec:decode', 'annotation':'response decoded:(PB2T | B2T)'},
                    (
                        {'label': 'riakc_pb_socket:send_caller'},
                        {'label' : 'gen_server:reply'}
                    )
                ]
            )
        ]
    )
    
    #------------------------------------------------------------
    # riak_api_pb_server
    #------------------------------------------------------------

    riakapi = Node({'label': 'riak_api_pb_server',       'color': fsm_color})

    riakapi.append(
        (
            {'label': 'riak_api_pb_server:connected'},
            [
                {'label': 'riak_kv_ts_svc:decode', 'annotation':'request decoded:(PB2T | B2T)'},
                {'label': 'riak_api_pb_server:process_message'},
            ],
            [
                (
                    {'label': 'riak_kv_ts_svc:process'},
                    {'label': 'riak_kv_ts_svc:check_table_and_call'},
                    [
                        {'label': 'riak_kv_ts_util:get_table_ddl'},
                        (
                            {'label': 'riak_kv_ts_svc:sub_tsqueryreq'},
                            {'label': 'riak_kv_qry:submit'},
                            [
                                (
                                    {'label': 'riak_ql_lexer:get_tokens'},
                                    {'label': 'riak_ql_parser:parse'},
                                ),
                                (
                                    {'label': 'riak_kv_qry:do_select'},
                                    [
                                        {'label': 'riak_kv_qry_compiler:compile'},
                                        (
                                            {'label': 'riak_kv_qry_queue:put_on_queue'},
                                            {'tag':'gen_server_call2', 'label': 'gen_server:call'}
                                        ),
                                        {'label': 'riak_kv_qry:maybe_await_query_results'}
                                    ]
                                )
                            ]
                        )
                    ]
                ),
                (
                    {'label': 'riak_api_pb_server:send_encoded_message_or_error'},
                    {'label': 'riak_pb_codec:encode', 'annotation':'response encoded:(T2PB | T2B)'},
                    {'label': 'riak_api_pb_server:send_message'},
                )
            ]
        )
    )

    #------------------------------------------------------------
    # riak_kv_qry_queue
    #------------------------------------------------------------

    riak_kv_qry_queue = Node({'label': 'riak_kv_qry_queue',       'color': server_color})
    riak_kv_qry_queue.append(({'label': 'riak_kv_qry_queue:handle_call'},
                              {'label': 'riak_kv_qry_queue:do_push_query'},
                              {'label': 'queue:in'}))

    #------------------------------------------------------------
    # riak_kv_qry_worker
    #------------------------------------------------------------

    riak_kv_qry_worker = Node({'label': 'riak_kv_qry_worker',       'color': server_color})

    handle_info = riak_kv_qry_worker.append({'label':'riak_kv_qry_worker:handle_info'})

    riak_kv_qry_worker.setNodeAttr('riak_kv_qry_worker:handle_info', 'rank', 'same')

    handle_info.append(
        [
            (
                {'label': 'riak_kv_qry_worker:pop_next_query'},
                {'label': 'riak_kv_qry_worker:execute_query'},
                {'label': 'riak_kv_qry_worker:run_sub_qs_fn'},
                (
                    {'label': 'riak_kv_index_fsm_sup:start_index_fsm'},
                    [
                        {'label': 'supervisor:start_child'},
                        {'label': 'riak_kv_stat:update'},
                    ]
                ),
            ),
            (
                {'label': 'riak_kv_qry_worker:add_subquery_result'},
                {'label': 'riak_kv_qry_worker:decode_results', 'annotation':'records decoded:(MSGPACK2T)'}
            ),
            {'label': 'riak_kv_qry_worker:subqueries_done'},
        ]
    )

    #------------------------------------------------------------
    # riak_kv_index_fsm
    #------------------------------------------------------------

    riak_kv_index_fsm = Node({'label':'riak_kv_index_fsm', 'color':fsm_color})
#    riak_kv_index_fsm.setNodeAttr('riak_kv_index_fsm', 'rank', 'same')

    riak_kv_index_fsm.append(
        [
            (
                {'label':'riak_core_coverage_fsm:init'},
                [
                    {'label':'riak_kv_index_fsm:module_info'},
                    {'label':'riak_kv_index_fsm:init'},
                    {'label':'riak_core_coverage_fsm:maybe_start_timeout_timer'},
                    {'label':'riak_core_coverage_fsm:plan_callback'},
                    {'label':'riak_core_coverage_fsm:plan_results_callback'}
                ]
            ),
            (
                {'label':'riak_core_coverage_fsm:initialize'},
                {'label':'riak_core_vnode_master:coverage'},
                {'label':'riak_core_vnode_master:proxy_cast'},
                {'tag':'gen_fsm1', 'label':'gen_fsm:send_event'}
            ),
            (
                {'label':'riak_core_coverage_fsm:waiting_results'},
                [
                    (
                        {'label':'riak_kv_index_fsm:process_results'},
                        [
                            {'label':'riak_kv_index_fsm:process_query_results'},
                            {'label':'riak_kv_vnode:ack_keys'},
                        ]
                    ),
                    {'label':'riak_kv_index_fsm:finish'},
                ]
            ),
        ]
    )

    riak_kv_index_fsm.setNodeAttr('riak_core_coverage_fsm:waiting_results', 'rank', 'same')

    #------------------------------------------------------------
    # riak_core_vnode_worker
    #------------------------------------------------------------
    
    riak_core_vnode_worker = Node({'label':'riak_core_vnode_worker', 'color':server_color})
    riak_core_vnode_worker.append(
        (
            {'label':'riak_core_vnode_worker:handle_cast'},
            {'label':'riak_kv_worker:handle_work'},
            [
                {'label':'eleveldb:fold', 'annotation':'records decoded:(MSGPACK2C++):(when filter present)'},
                (
                    {'label':'riak_kv_vnode:result_fun_ack'},
                    {'tag':'vnode_reply1', 'label':'riak_core_vnode:reply'}
                ),
                (
                    {'label':'riak_kv_vnode:finish_fold'},
                    {'tag':'vnode_reply2', 'label':'riak_core_vnode:reply'}
                )
            ]
        )
    )

    #------------------------------------------------------------
    # riak_core_vnode_worker_pool
    #------------------------------------------------------------
    
    riak_core_vnode_worker_pool = Node({'label':'riak_core_vnode_worker_pool', 'color':fsm_color})
    riak_core_vnode_worker_pool.append(
        (
            {'label':'riak_core_vnode_worker_pool:handle_event'},
            {'label':'riak_core_vnode_worker:handle_work'},
            {'label':'gen_server:cast'},
        )
    )

    #------------------------------------------------------------
    # riak_core_vnode
    #------------------------------------------------------------
    
    riak_core_vnode = Node({'label':'riak_core_vnode', 'color':fsm_color})
    riak_core_vnode.append(
        (
            {'label':'riak_core_vnode:handle_event'},
            {'label':'riak_core_vnode:active'},
            {'label':'riak_core_vnode:vnode_coverage'},
            [
                {'label':'riak_kv_vnode:handle_coverage'},
                (
                    {'label':'riak_core_vnode_worker_pool:handle_work'},
                    {'tag':'gen_fsm2', 'label':'gen_fsm:send_event'},
                )
            ]
        )
    )
        
    test.append(riakc)
    test.append(riakpb)
    test.append(riakapi)
    test.append(riak_kv_qry_queue)
    test.append(riak_kv_qry_worker)
    test.append(riak_kv_index_fsm)
    test.append(riak_core_vnode_worker)
    test.append(riak_core_vnode_worker_pool)
    test.append(riak_core_vnode)
    test.append(getLegend())

    if True:
        test.edge('gen_server_call1',                                 'riakc_pb_socket:send_request',          {'color':server_color, 'label':' 1 '})
        test.edge('gen_tcp:send',                                     'riak_api_pb_server:connected',          {'color':fsm_color,    'label':' 2 '})
        test.edge('gen_server:call2',                                 'riak_kv_qry_queue:do_push_query',       {'color':server_color, 'label':' 3 '})
        test.edge('queue:in',                                         'riak_kv_qry_worker:pop_next_query',     {'color':server_color, 'label':' 4 '})
        test.edge('supervisor:start_child',                           'riak_core_coverage_fsm:init',           {'color':fsm_color,    'label':' 5 ', 'dir':'both', 'arrowhead':'diamond', 'arrowtail':'diamond'})
        test.edge('gen_fsm1',                                         'riak_core_vnode:active',                {'color':internode_color,    'label':' 6 ', 'arrowhead':'diamond'})
        test.edge('gen_fsm2',                                         'riak_core_vnode_worker:handle_work',    {'color':fsm_color,    'label':' 7 '})
        test.edge('gen_server:cast',                                  'riak_kv_worker:handle_work',            {'color':server_color, 'label':' 8 '})
        
        test.edge('vnode_reply1',                                     'riak_kv_index_fsm:process_results',     {'color':internode_color,    'label':' 9 ', 'arrowhead':'diamond'})
        test.edge('riak_kv_index_fsm:process_query_results',          'riak_kv_qry_worker:add_subquery_result',{'color':server_color, 'label':' 10 '})
        test.edge('riak_kv_vnode:ack_keys',                           'riak_kv_vnode:result_fun_ack',          {'color':server_color, 'label':' 11 '})
        test.edge('vnode_reply2',                                     'riak_kv_index_fsm:finish',              {'color':internode_color,    'label':' 12 ', 'arrowhead':'diamond'})
        test.edge('riak_kv_index_fsm:finish',                         'riak_kv_qry_worker:subqueries_done',    {'color':server_color, 'label':' 13 '})
        test.edge('riak_kv_qry_worker:subqueries_done',               'riak_kv_qry:maybe_await_query_results', {'color':server_color, 'label':' 14 '})
        test.edge('riak_api_pb_server:send_message',                  'riakc_pb_socket:handle_info',           {'color':server_color, 'label':' 15 '})
        test.edge('gen_server:reply',                                 'gen_server_call1',                      {'color':server_color, 'label':' 16 '})

    return

#-----------------------------------------------------------------------
# Get a digraph object representing the TS put path
#-----------------------------------------------------------------------

def getTs1_3PutDiGraph(outputPrefix,
                       nRecord,
                       clientFileName,     serverFileName,
                       clientCompFileName, profilerBaseFileName):
    
    test = DiGraph()
    
    test.nOp = int(nRecord)
    
    test.ingestProfilerOutput(clientFileName,     serverFileName,
                              None, None,
                              clientCompFileName, profilerBaseFileName,
                              "total")

    addTs1_3PutNodes(test)

    return test

def getTs1_1PutDiGraph(outputPrefix,
                       nRecord,
                       clientFileName,     serverFileName,
                       clientCompFileName, profilerBaseFileName):
    
    test = DiGraph()
    
    test.nOp = int(nRecord)
    
    test.ingestProfilerOutput(clientFileName,     serverFileName,
                              None, None,
                              clientCompFileName, profilerBaseFileName,
                              "total")

    addTs1_1PutNodes(test)

    return test

#-----------------------------------------------------------------------
# Make a graph of the TS put path
#-----------------------------------------------------------------------

def makeTs1_1PutGraph(outputPrefix,
                   nRecord, 
                   clientFileName,     serverFileName,
                   clientCompFileName, profilerBaseFileName):

    test = getTs1_1PutDiGraph(outputPrefix,
                           nRecord,
                           clientFileName,     serverFileName,
                           clientCompFileName, profilerBaseFileName)

    test.title(['Riak TS1.1 Put Path', getTimeStr(test.totalUsec/test.nOp) + ' per put'])

    test.render(outputPrefix)


def makeTs1_3PutGraph(outputPrefix,
                   nRecord, 
                   clientFileName,     serverFileName,
                   clientCompFileName, profilerBaseFileName):

    test = getTs1_3PutDiGraph(outputPrefix,
                           nRecord,
                           clientFileName,     serverFileName,
                           clientCompFileName, profilerBaseFileName)

    test.title(['Riak TS1.3 Put Path', getTimeStr(test.totalUsec/test.nOp) + ' per put'])

    test.render(outputPrefix)

#-----------------------------------------------------------------------
# Get a digraph object representing the query path
#-----------------------------------------------------------------------

def getQueryDiGraph(outputPrefix,
                    nRecord, nQuery,
                    clientFileName,     serverFileName,
                    clientBaseFileName, serverBaseFileName,
                    clientCompFileName, profilerBaseFileName):
    
    test = DiGraph()
    
    test.nRecord = int(nRecord)
    test.nQuery  = int(nQuery)
    
    test.ingestProfilerOutput(clientFileName,     serverFileName,
                              clientBaseFileName, serverBaseFileName,
                              clientCompFileName, profilerBaseFileName)

    addTsQueryNodes(test)

    return test

#-----------------------------------------------------------------------
# Make a graph of the query path
#-----------------------------------------------------------------------

def makeQueryGraph(outputPrefix,
                   nRecord, nQuery,
                   clientFileName,     serverFileName,
                   clientBaseFileName, serverBaseFileName,
                   clientCompFileName, profilerBaseFileName):

    test = getQueryDiGraph(outputPrefix,
                           nRecord, nQuery,
                           clientFileName,     serverFileName,
                           clientBaseFileName, serverBaseFileName,
                           clientCompFileName, profilerBaseFileName)

    if test.nRecord > 1:
        recStr = str(test.nRecord) + ' records per query'
    else:
        recStr = str(test.nRecord) + ' record per query'
        
    test.title(['RiakTS Query Path', recStr, getTimeStr(test.totalUsec/test.nQuery) + ' per query'])

    test.render(outputPrefix)

def getQueryDiGraphByConstruction(dirPrefix, optsList, outputPrefix):

    [nRecord, nQuery, useFilter, target] = getOptList(optsList)

    dirName = dirPrefix + '/ts_query_' + str(nRecord) + '_' + str(nQuery)
    if useFilter != None:
        dirName = dirName + '_' + str(useFilter)
    else:
        dirName = dirName + '_false'
        
    if target != None:
        dirName = dirName + '_' + str(target)

    dirName = dirName + '_output'
            
    clientFileName = dirName + '/client.txt'
    serverFileName = dirName + '/server.txt'

    clientBaseFileName = dirName + '/clientbase.txt'
    serverBaseFileName = dirName + '/serverbase.txt'

    clientCompFileName   = dirName + '/clientcomp.txt'
    profilerBaseFileName = dirName + '/profbase.txt'
    
    graph = getQueryDiGraph(outputPrefix,
                            nRecord, nQuery,
                            clientFileName,     serverFileName,
                            clientBaseFileName, serverBaseFileName,
                            clientCompFileName, profilerBaseFileName)
    return graph

#-----------------------------------------------------------------------
# Difference two digraphs
#-----------------------------------------------------------------------

def hasKey(d, key):
    if key in d.keys():
        return 'True'
    else:
        return 'False'

def getOptList(optList):
    useFilter=None
    target=None
    if len(optList) == 2:
        [nRecord, nQuery] = optList
    elif len(optList) == 3:
        [nRecord, nQuery, useFilter] = optList
    elif len(optList) == 4:
        [nRecord, nQuery, useFilter, target] = optList

    if useFilter != None:
        if useFilter:
            useFilter = 'true'
        else:
            useFilter = 'false'
            
    return [nRecord, nQuery, useFilter, target]

def getDeltaStr(list1, list2):

    [nRecord1, nQuery1, useFilter1, target1] = getOptList(list1)
    [nRecord2, nQuery2, useFilter2, target2] = getOptList(list2)

    deltaStr = str(nRecord2)
    openBrace = False
    if useFilter2 != None:
        deltaStr = deltaStr + ' (filter = ' + str(useFilter2)
        openBrace = True
    if target2 != None:
        if ~openBrace:
            deltaStr += '('
        else:
            deltaStr += ', '
        deltaStr = deltaStr + ', ' + target2

    if openBrace:
        deltaStr = deltaStr + ')'        

    deltaStr = deltaStr  + ' &rarr; '

    deltaStr = deltaStr + str(nRecord1)
    openBrace = False
    if useFilter1 != None:
        deltaStr = deltaStr + ' (filter = ' + str(useFilter1)
        openBrace = True
    if target1 != None:
        deltaStr = deltaStr + ', ' + target2
        if ~openBrace:
            deltaStr += '('
        else:
            deltaStr += ', '

    if openBrace:
        deltaStr = deltaStr + ')'        

    return deltaStr
    
def makeDiffGraph(dirPrefix, list1, list2, outputPrefix, deltaFrac, threshold):

    graph1 = getQueryDiGraphByConstruction(dirPrefix, list1, outputPrefix)
    graph2 = getQueryDiGraphByConstruction(dirPrefix, list2, outputPrefix)

    #------------------------------------------------------------
    # Construct delta string
    #------------------------------------------------------------
    
    deltaStr = getDeltaStr(list1, list2)
    
    deltaTimeStr = '&Delta;t = ' + getTimeStr(graph1.totalUsec/(graph1.nQuery) - graph2.totalUsec/(graph2.nQuery), True)

    delta = graph1.totalUsec/(graph1.nQuery) - graph2.totalUsec/(graph2.nQuery)
    if delta < 0:
        color = 'darkgreen'
    else:
        color = 'red'
        
    graph1.title(['RiakTS Query Path', deltaStr + ' records per query', (deltaTimeStr + ' per query', color)])

    for key in graph1.profilerActualDict.keys():
        if isinstance(graph1.profilerActualDict[key], dict):
            print 'Key = ' + key + ' t1 = ' + str(graph1.profilerActualDict[key]['corrusec']/graph1.nQuery)
            print 'Key = ' + key + ' t2 = ' + str(graph2.profilerActualDict[key]['corrusec']/graph2.nQuery)
            graph1.profilerActualDict[key]['corrusec'] = graph1.profilerActualDict[key]['corrusec']/graph1.nQuery - graph2.profilerActualDict[key]['corrusec']/graph2.nQuery
            graph1.profilerActualDict[key]['frac'] = graph1.profilerActualDict[key]['frac'] - graph2.profilerActualDict[key]['frac']

    graph1.refUsec   = graph1.totalUsec/graph1.nQuery
    graph1.threshold = threshold
    graph1.isDelta   = True
    graph1.deltaFrac = deltaFrac

    graph1.nQuery    = 1

                        
    graph1.render(outputPrefix)

def doit():
#    makeDiffGraph('/Users/eml/projects/riak/riak_test/riak_test_query/', [1, 10000], [100, 1000], 'ts_query_100-1')
#    makeDiffGraph('/Users/eml/projects/riak/riak_test/riak_test_query/', [100, 1000], [1000, 1000], 'ts_query_1000-100')
#    makeDiffGraph('/Users/eml/projects/riak/riak_test/riak_test_query/', [1000, 1000],               [1,   10000], 'ts_query_1000-1', True, 1.0)
#    makeDiffGraph('/Users/eml/projects/riak/riak_test/riak_test_query/', [1000, 1000,  'uc_debug7'], [1000, 1000], 'ts_query_1000_ttb-1000', False, 1000.0)
    makeDiffGraph('/Users/eml/projects/riak/riak_test/riak_test_query/', [1000, 1000,  True], [1000, 1000], 'ts_query_1000_filter-none', False, 1000.0)

def graphTsListKeys():
    d = DiGraph()
    addTsListKeysNodes(d)
    d.title('Riak TS Listkeys Path')
    d.render('tslistkeys')

def graphTsQuery():
    d = DiGraph()
    addTsQueryNodes(d)
    d.title('Riak TS Query Path')
    d.render('tsquery')

def graphTs1_1Put():
    d = DiGraph()
    addTs1_1PutNodes(d)
    d.title('Riak TS1.1 Put Path')
    d.render('ts1.1put')

def graphTs1_3Put():
    d = DiGraph()
    addTs1_3PutNodes(d)
    d.title('Riak TS1.3 Put Path')
    d.render('ts1.3put')

def graphPut():
    d = DiGraph()
    addPutNodes(d)
    d.title('Riak Normal Put Path')
    d.render('put')

def graphReadRepair():
    d = DiGraph()
    addReadRepairNodes(d)
    d.title('Riak Read Repair Path')
    d.render('rr')

def graphW1cPut():
    d = DiGraph()
    addW1cPutNodes(d)
    d.title('Riak W1C Put Path')
    d.render('w1cput')

def graphGet():
    d = DiGraph()
    addGetNodes(d)
    d.title('Riak Normal Get Path')
    d.render('get')

def graphAae():
    d = DiGraph()
    addAaeNodes(d)
    d.title('Riak AAE  Path')
    d.render('aae')

def makeGraphs():
    graphTsQuery()
    graphTs1_1Put()
    graphTs1_3Put()
    graphPut()
    graphGet()
    graphW1cPut()
    graphTsListKeys()
    graphReadRepair()
    graphAae()

    
