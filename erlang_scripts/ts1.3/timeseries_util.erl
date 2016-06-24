%% -*- Mode: Erlang -*-
%% -------------------------------------------------------------------
%%
%% Copyright (c) 2015 Basho Technologies, Inc.
%%
%% This file is provided to you under the Apache License,
%% Version 2.0 (the "License"); you may not use this file
%% except in compliance with the License.  You may obtain
%% a copy of the License at
%%
%%   http://www.apache.org/licenses/LICENSE-2.0
%%
%% Unless required by applicable law or agreed to in writing,
%% software distributed under the License is distributed on an
%% "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
%% KIND, either express or implied.  See the License for the
%% specific language governing permissions and limitations
%% under the License.
%%
%% -------------------------------------------------------------------
%% @doc A util module for riak_ts basic CREATE TABLE Actions
-module(timeseries_util).

-compile(export_all).

-include_lib("eunit/include/eunit.hrl").

-define(MAXVARCHARLEN,       16).
-define(MAXTIMESTAMP,        trunc(math:pow(2, 63))).
-define(MAXFLOAT,            math:pow(2, 63)).
-define(MULTIPLECLUSTERSIZE, 3).
-define(LARGECLUSTERSIZE, 5).

confirm_create(ClusterType, DDL, Expected) ->

    [Node | _] =build_cluster(ClusterType),

    Props = io_lib:format("{\\\"props\\\": {\\\"n_val\\\": 3, \\\"table_def\\\": \\\"~s\\\"}}", [DDL]),
    Got = rt:admin(Node, ["bucket-type", "create", get_bucket(), lists:flatten(Props)]),
    ?assertEqual(Expected, Got),

    pass.

confirm_activate(ClusterType, DDL, Expected) ->

    [Node | Rest] = build_cluster(ClusterType),
    ok = maybe_stop_a_node(ClusterType, Rest),
    {ok, _} = create_bucket(Node, DDL, 3),
    Got     = activate_bucket(Node, DDL),
    ?assertEqual(Expected, Got),

    pass.

confirm_put(ClusterType, TestType, DDL, Obj) ->

    [Node | _]  = build_cluster(ClusterType),
    
    case TestType of
	normal ->
	    io:format("1 - Creating and activating bucket~n"),
	    {ok, _} = create_bucket(Node, DDL, 3),
	    {ok, _} = activate_bucket(Node, DDL);
	n_val_one ->
	    io:format("1 - Creating and activating bucket~n"),
	    {ok, _} = create_bucket(Node, DDL, 1),
	    {ok, _} = activate_bucket(Node, DDL);
	no_ddl ->
	    io:format("1 - NOT Creating or activating bucket - failure test~n"),
	    ok
    end,
    Bucket = list_to_binary(get_bucket()),
    io:format("2 - writing to bucket ~p with:~n- ~p~n", [Bucket, Obj]),
    C = rt:pbc(Node),
    riakc_ts:put(C, Bucket, Obj).

confirm_select(ClusterType, TestType, DDL, Data, Qry, Expected) ->
    
    [Node | _] = build_cluster(ClusterType),
    
    case TestType of
	normal ->
	    io:format("1 - Create and activate the bucket~n"),
	    {ok, _} = create_bucket(Node, DDL, 3),
	    {ok, _} = activate_bucket(Node, DDL);
	n_val_one ->
	    io:format("1 - Creating and activating bucket~n"),
	    {ok, _} = create_bucket(Node, DDL, 1),
	    {ok, _} = activate_bucket(Node, DDL);
	no_ddl ->
	    io:format("1 - NOT Creating or activating bucket - failure test~n"),
	    ok
    end,
    
    Bucket = list_to_binary(get_bucket()),
    io:format("2 - writing to bucket ~p with:~n- ~p~n", [Bucket, Data]),
    C = rt:pbc(Node),
    ok = riakc_ts:put(C, Bucket, Data),
    
    io:format("3 - Now run the query ~p~n", [Qry]),
    Got = riakc_ts:query(C, Qry), 
    io:format("Got is ~p~n", [Got]),
    ?assertEqual(Expected, Got),
    pass.

%%
%% Helper funs
%%

activate_bucket(Node, _DDL) ->
    rt:admin(Node, ["bucket-type", "activate", get_bucket(api)]).

activate_bucket(Node, _DDL, Api) ->
    rt:admin(Node, ["bucket-type", "activate", get_bucket(Api)]).

create_bucket(Node, NVal) ->
    create_bucket(Node, NVal, false).

create_bucket(Node, DDL, NVal) when is_integer(NVal) ->
    create_bucket(Node, DDL, NVal, api);

create_bucket(Node, NVal, WriteOnce) ->
    case WriteOnce of
	false ->
	    Props = io_lib:format("{\\\"props\\\": {\\\"n_val\\\": " ++ 
				      integer_to_list(NVal) ++
				      "}}", []),
	    rt:admin(Node, ["bucket-type", "create", get_bucket(), 
			    lists:flatten(Props)]);
	true ->
%	    create_bucket_type(Node, get_bucket(), [{write_once, true}, {n_val, 1}])
	    Props = io_lib:format("{\\\"props\\\": {\\\"n_val\\\": " ++ 
				      integer_to_list(NVal) ++
				      ", \\\"write_once\\\": true}}", []),
	    rt:admin(Node, ["bucket-type", "create", get_bucket(),
			    lists:flatten(Props)])
    end.

create_bucket(Node, DDL, NVal, Api) when is_integer(NVal) ->
    Props = io_lib:format("{\\\"props\\\": {\\\"n_val\\\": " ++ 
			      integer_to_list(NVal) ++
			      ", \\\"table_def\\\": \\\"~s\\\"}}", [DDL]),
    Args = ["bucket-type", "create", get_bucket(Api), lists:flatten(Props)],
    io:format("Calling admin with Args = ~p~n", [Args]),
    rt:admin(Node, Args).

create_bucket_type(Nodes, Type, Props) ->
    lager:info("Create bucket type ~p, wait for propagation", [Type]),
    rt:create_and_activate_bucket_type(Nodes, Type, Props),
    rt:wait_until_bucket_type_status(Type, active, Nodes),
    rt:wait_until_bucket_props(Nodes, {Type, <<"bucket">>}, Props),
    ok.

%% @ignore
maybe_stop_a_node(one_down, [H | _T]) ->
    ok = rt:stop(H);
maybe_stop_a_node(_, _) ->
    ok.

disable_aae() ->
    Opts = [{anti_entropy, {off, []}}],
    rtdev:update_app_config(all, [{riak_kv, Opts}]).

set_worker_pool_size() ->
    Opts = [{worker_pool_size, 8}],
    rtdev:update_app_config(all, [{riak_kv, Opts}]).

set_max_quanta() ->
    Opts = [{timeseries_query_max_quanta_span, 1000}],
    rtdev:update_app_config(all, [{riak_kv, Opts}]).

set_ring_size() ->
    Opts = [{ring_size, 8}],
    rtdev:update_app_config(all, [{riak_core, Opts}]).

set_ring_size(Ringsize) ->
    lager:info("Setting ring size to ~p~n", [Ringsize]),
    Opts = [{ring_creation_size, Ringsize}],
    rtdev:update_app_config(all, [{riak_core, Opts}]).

build_cluster(Nnode, Ringsize) ->
    set_ring_size(Ringsize),
    build_c2(Nnode, []).
    
build_cluster(single)   -> build_c2(1);
build_cluster(oddring)  -> build_c2(?MULTIPLECLUSTERSIZE, oddring);
build_cluster(multiple) -> build_c2(?MULTIPLECLUSTERSIZE);
build_cluster(large)    -> build_c2(?LARGECLUSTERSIZE);
build_cluster(one_down) -> build_c2(?MULTIPLECLUSTERSIZE).

-spec build_c2(non_neg_integer()) -> [node()].
build_c2(Size) ->
    lager:info("Building cluster of ~p~n", [Size]),
    build_c2(Size, []).
-spec build_c2(non_neg_integer(), [list()|atom()]) -> [node()].

build_c2(Size, oddring) ->
    lager:info("Building oddring cluster of ~p~n", [Size]),
    set_ring_size(),
    build_c2(Size, []);
build_c2(Size, Config) ->
    rt:set_backend(eleveldb),
    disable_aae(),
    set_worker_pool_size(),
    set_max_quanta(),
    [_Node1|_] = Nodes = rt:deploy_nodes(Size, Config),
    rt:join_cluster(Nodes),
    Nodes.

get_bucket(Ind) when is_integer(Ind) ->
    "Gen" ++ integer_to_list(Ind);
get_bucket(api) ->
    "GeoCheckin";
get_bucket(bede) ->
    "Bede";
get_bucket(brianbede) ->
    "action".

get_bucket() ->
    "GeoCheckin".

get_valid_qry() ->
    "select * from GeoCheckin Where time > 1 and time < 10 and myfamily = 'family1' and myseries ='seriesX'".

get_invalid_qry(borked_syntax) ->
    "selectah * from GeoCheckin Where time > 1 and time < 10";
get_invalid_qry(key_not_covered) ->
    "select * from GeoCheckin Where time > 1 and time < 10";
get_invalid_qry(invalid_operator) ->
    "select * from GeoCheckin Where time > 1 and time < 10 and myfamily = 'family1' and myseries ='seriesX' and weather > 'bob'";
get_invalid_qry(field_comparison) ->
    "select * from GeoCheckin Where time > 1 and time < 10 and myfamily = 'family1' and myseries ='seriesX' and weather = family1";
get_invalid_qry(type_error) ->
    "select * from GeoCheckin Where time > 1 and time < 10 and myfamily = 'family1' and myseries ='seriesX' and weather > true".

get_valid_select_data() ->
    Family = <<"family1">>,
    Series = <<"seriesX">>,
    Times = lists:seq(1, 10),
    [[Family, Series, X, get_varchar(), get_float()] || X <- Times].


-define(SPANNING_STEP, (1000*60*5)).

get_valid_qry_spanning_quanta() ->
    StartTime = 1 + ?SPANNING_STEP *  1,
    EndTime   = 1 + ?SPANNING_STEP * 10,
    lists:flatten(
      io_lib:format("select * from GeoCheckin Where time > ~b and time < ~b"
                    " and myfamily = 'family1' and myseries = 'seriesX'",
                    [StartTime, EndTime])).

get_valid_select_data_spanning_quanta() ->
    Family = <<"family1">>,
    Series = <<"seriesX">>,
    Times = lists:seq(1 + ?SPANNING_STEP, 1 + ?SPANNING_STEP * 10, ?SPANNING_STEP),  %% five-minute intervals, to span 15-min buckets
    [[Family, Series, X, get_varchar(), get_float()] || X <- Times].


get_cols(docs) ->
    [<<"myfamily">>,
     <<"myseries">>,
     <<"time">>,
     <<"weather">>,
     <<"temperature">>].

exclusive_result_from_data(Data, Start, Finish) when is_integer(Start)   andalso
						     is_integer(Finish)  andalso
						     Start  > 0          andalso
						     Finish > 0          andalso
						     Finish > Start ->
    [list_to_tuple(X) || X <- lists:sublist(Data, Start, Finish - Start + 1)].

remove_last(Data) ->
    lists:reverse(tl(lists:reverse(Data))).

%% a valid DDL - the one used in the documents
get_ddl(docs) ->
    _SQL = "CREATE TABLE GeoCheckin (" ++
	"myfamily    varchar   not null, " ++
	"myseries    varchar   not null, " ++
	"time        timestamp not null, " ++
	"weather     varchar   not null, " ++
	"temperature float, " ++
	"PRIMARY KEY ((quantum(time, 15, 'm'), myfamily, myseries), " ++
	"time, myfamily, myseries))";
%% another valid DDL - one with all the good stuff like
%% different types and optional blah-blah
get_ddl(variety) ->
    _SQL = "CREATE TABLE GeoCheckin (" ++
	"myfamily    varchar     not null, " ++
	"myseries    varchar     not null, " ++
	"time        timestamp   not null, " ++
	"myint       integer     not null, " ++
	"myfloat     float       not null, " ++
	"mybool      boolean     not null, " ++
	"mytimestamp timestamp   not null, " ++
	"myany       any         not null, " ++
	"myoptional  integer, " ++
	"PRIMARY KEY ((quantum(time, 15, 'm'), myfamily, myseries), " ++
	"time, myfamily, myseries))";
%% an invalid TS DDL becuz family and series not both in key
get_ddl(shortkey_fail) ->
    _SQL = "CREATE TABLE GeoCheckin (" ++
	"myfamily    varchar   not null, " ++
	"myseries    varchar   not null, " ++
	"time        timestamp not null, " ++
	"weather     varchar   not null, " ++
	"temperature float, " ++
	"PRIMARY KEY ((quantum(time, 15, 'm'), myfamily), " ++
	"time, myfamily))";
%% an invalid TS DDL becuz partition and local keys dont cover the same space
get_ddl(splitkey_fail) ->
    _SQL = "CREATE TABLE GeoCheckin (" ++
	"myfamily    varchar   not null, " ++
	"myseries    varchar   not null, " ++
	"time        timestamp not null, " ++
	"weather     varchar   not null, " ++
	"temperature float, " ++
	"PRIMARY KEY ((quantum(time, 15, 'm'), myfamily, myseries), " ++
	"time, myfamily, myseries, temperature))";
%% another invalid TS DDL because family/series must be varchar
%% or is this total bollox???
get_ddl(keytype_fail_mebbies_or_not_eh_check_it_properly_muppet_boy) ->
    _SQL = "CREATE TABLE GeoCheckin (" ++
	"myfamily    integer   not null, " ++
	"myseries    varchar   not null, " ++
	"time        timestamp not null, " ++
	"weather     varchar   not null, " ++
	"temperature float, " ++
	"PRIMARY KEY ((quantum(time, 15, 'm'), myfamily, myseries), " ++
	"time, myfamily, myseries))".

get_valid_obj() ->
    [get_varchar(),
     get_varchar(),
     get_timestamp(),
     get_varchar(),
     get_float()].

get_invalid_obj() ->
    [get_varchar(),
     get_integer(),   % this is the duff field
     get_timestamp(),
     get_varchar(),
     get_float()].

get_varchar() ->
    Len = random:uniform(?MAXVARCHARLEN),
    String = get_string(Len),
    list_to_binary(String).

get_string(Len) ->
    get_s(Len, []).

get_integer() ->
    get_timestamp().

get_s(0, Acc) ->
    Acc;
get_s(N, Acc) when is_integer(N) andalso N > 0 ->
    get_s(N - 1, [random:uniform(255) | Acc]).

get_timestamp() ->
    random:uniform(?MAXTIMESTAMP).

get_float() ->
    F1 = random:uniform(trunc(?MAXFLOAT)),
    F2 = random:uniform(trunc(?MAXFLOAT)),
    F1 - F2 + random:uniform().
