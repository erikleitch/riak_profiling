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

-module(ts_api_util).

-compile(export_all).

-include_lib("eunit/include/eunit.hrl").

%------------------------------------------------------------
% Cluster setup only. 
%------------------------------------------------------------

build_and_activate_cluster_timeseries(ClusterType, TestType, DDL) ->
    build_and_activate_cluster(ClusterType, TestType, DDL, api).

build_and_activate_cluster_bede(ClusterType, TestType, DDL) ->
    build_and_activate_cluster(ClusterType, TestType, DDL, bede).

build_and_activate_cluster_brianbede(ClusterType, TestType, DDL) ->
    build_and_activate_cluster(ClusterType, TestType, DDL, brianbede).

build_and_activate_cluster(ClusterType, TestType, DDL, Api) ->
    [Node | _] = timeseries_util:build_cluster(ClusterType),
    
    case TestType of
	normal ->
	    io:format("1 - Create and activate the bucket (0)~n"),
	    {ok, _} = timeseries_util:create_bucket(Node, DDL, 3, Api),
	    {ok, _} = timeseries_util:activate_bucket(Node, DDL, Api);
	n_val_two ->
	    io:format("1 - Create and activate the bucket (0)~n"),
	    {ok, _} = timeseries_util:create_bucket(Node, DDL, 2, Api),
	    {ok, _} = timeseries_util:activate_bucket(Node, DDL, Api);
	n_val_four ->
	    io:format("1 - Create and activate the bucket (0)~n"),
	    {ok, _} = timeseries_util:create_bucket(Node, DDL, 4, Api),
	    {ok, _} = timeseries_util:activate_bucket(Node, DDL, Api);
	n_val_one ->
	    io:format("1 - Create and activate the bucket (0)~n"),
	    {ok, _} = timeseries_util:create_bucket(Node, DDL, 1, Api),
	    {ok, _} = timeseries_util:activate_bucket(Node, DDL, Api);
	no_ddl ->
	    io:format("1 - NOT Creating or activating bucket - failure test~n"),
	    ok
    end,
    Bucket = list_to_binary(timeseries_util:get_bucket(Api)),
    C = rt:pbc(Node),
    [C, Bucket].

%------------------------------------------------------------
% Writes N sequential records (incrementing time) via either the
% normal put path, or the timeseries path (switch on Ts)
%------------------------------------------------------------

setup_cluster_timeseries(ClusterType, TestType, DDL, N, Incr, Ts) ->
    [C, Bucket] = build_and_activate_cluster_timeseries(ClusterType, TestType, DDL),

    Data = [[<<"family1">>, <<"seriesX">>, 100, 1, <<"test1">>, 1.0, true]],
    io:format("Time before = ~p~n", [my_time()]),
    ok = putDataModTime(C, Bucket, Data, N, Incr, Ts),
    io:format("Time after = ~p~n", [my_time()]),
    C.

setup_cluster_listkeys(ClusterType, TestType, DDL, N, Incr, Ts) ->
    [C, Bucket] = build_and_activate_cluster_timeseries(ClusterType, TestType, DDL),

    Data = [[<<"family1">>, <<"seriesX">>, 100, 1, <<"test1">>, 1.0, true]],
    io:format("Time before = ~p~n", [my_time()]),
    ok = putDataModTime(C, Bucket, Data, N, Incr, Ts),
    io:format("Time after = ~p~n", [my_time()]),
    C.

my_time() ->
    {H, M, S} = time(),
        io_lib:format('~2..0b:~2..0b:~2..0b', [H, M, S]).

%------------------------------------------------------------
% Write data to riak:  
%
%  if Ts = true,  write via the timeseries path
%  if Ts = false, write via the normal put path
%------------------------------------------------------------

runQuery(Q, N) ->
    {ok, C} = riakc_pb_socket:start_link("127.0.0.1", 10017),
    runQuery(C, Q, N, N).
runQuery(_C, _Q, _N, 0) ->
    ok;
runQuery(C, Q, N, Acc) ->
    riakc_ts:query(C, Q),
    runQuery(C, Q, N, Acc-1).

%------------------------------------------------------------
% Write data to riak:  
%
%  if Ts = true,  write via the timeseries path
%  if Ts = false, write via the normal put path
%------------------------------------------------------------

putData(C, Bucket, Data, N, Ts) ->
    putData(C, Bucket, Data, N, N, Ts).
putData(_C, _Bucket, _Data, _N, 0, _Ts) ->
    ok;
putData(C, Bucket, Data, N, Acc, Ts) ->
    case Ts of
	true ->

	    case riakc_ts:put(C, Bucket, Data) of
		ok ->
		    ok;
		{error, Reason} ->
		    io:format("Got an error: ~p~n", [Reason])
	    end;

	false ->
	    Key = list_to_binary("key"++integer_to_list(Acc)),
	    Obj = riakc_obj:new({<<"GeoCheckin">>,<<"GeoCheckin">>}, Key, Data),
	    ok  = riakc_pb_socket:put(C, Obj)
    end,
    putData(C, Bucket, Data, N, Acc-1, Ts).

%------------------------------------------------------------
% Write data to riak, modifying the timestamp
%
%  if Ts = true,  write via the timeseries path
%  if Ts = false, write via the normal put path
%------------------------------------------------------------

putDataModTime(C, Bucket, Data, N, Incr, Ts) ->
    putDataModTime(C, Bucket, Data, N, N, Incr, Ts).
putDataModTime(_C, _Bucket, _Data, _N, 0, _Incr, _Ts) ->
    ok;
putDataModTime(C, Bucket, Data, N, Acc, Incr, Ts) ->
    Data2 = [{<<"family1">>, <<"seriesX">>, Acc*Incr, 1, <<"test1">>, 1.0, true}],
    case Ts of
	true ->
	    case riakc_ts:put(C, Bucket, Data2) of
		ok ->
		    ok;
		{error, Reason} ->
		    io:format("Got an error: ~p~n", [Reason])
	    end;
	false ->
	    Key = list_to_binary("key"++integer_to_list(Acc)),
	    Obj = riakc_obj:new(<<"GeoCheckin">>, Key, Data),
	    ok  = riakc_pb_socket:put(C, Obj)
    end,
    putDataModTime(C, Bucket, Data, N, Acc-1, Incr, Ts).

%------------------------------------------------------------
% Put Bede-style data for multiple users
%------------------------------------------------------------

putBedeUserData(C, Bucket, NUser, NData, Incr, Ts) ->
    putBedeUserData(C, Bucket, NUser, NData, Incr, Ts, 0).

putBedeUserData(_C, _Bucket, _NUser, _NData, _Incr, _Ts, _NUser) ->
    ok;
putBedeUserData(C, Bucket, NUser, NData, Incr, Ts, Acc) ->
    User = list_to_binary("user" ++ integer_to_list(Acc)),
    io:format("Putting data for user = ~p~n", [User]),
    putDataModTimeBede(C, Bucket, NData, Incr, Ts, User),
    putBedeUserData(C, Bucket, NUser, NData, Incr, Ts, Acc+1).

%------------------------------------------------------------
% Put Bede-style data for a single user
%------------------------------------------------------------

putDataModTimeBede(C, Bucket, N, Incr, Ts, User) ->
    putDataModTimeBede(C, Bucket, N, 0, Incr, Ts, User, 0.0).

putDataModTimeBede(_C, _Bucket, _N, _N, _Incr, _Ts, _User, _Stake) ->
    ok;
putDataModTimeBede(C, Bucket, N, Acc, Incr, Ts, UserId, Stake) ->
						% Payout is Odds * Amt

    Odds = 2.0,

						% Probability is the likelihood of winning (in percent)

    Prob = 48.0,

    UtcTime = (Acc+1)*Incr, 
    BedeRef = <<"bederef">>,
    Category = <<"category">>,
    Currency = <<"euros">>,
    EventDescription = <<"eventdesc">>,
    EventType = 0,
    Amount = getBedeStake(Acc, Stake),
    Description = <<"bet">>,
    Id = trunc(Acc/2),
    IsNew = true,
    ActionStatus = 0,
    Type = getBedeType(Acc, Prob),
    RemoteRef = <<"c4c26ff">>,
    SiteCode = <<"betuk">>,
    EventStatus = 0,

    Credit = 1.0,
    Debit  = 1.0,

    VoidedAtUtc = (Acc+1)*Incr, 

    case Type of
	<<"WIN">> ->
	    Payout = Amount * Odds;
	_ ->
	    Payout = Amount
    end,

    Data = [{UserId, UtcTime, BedeRef, Category, Currency, EventDescription,
	     EventType, Payout, Description, Id, IsNew, ActionStatus, Type,
	     RemoteRef, SiteCode, EventStatus, Credit, Debit, VoidedAtUtc}],

    case Ts of
	true ->
	    case riakc_ts:put(C, Bucket, Data) of
		ok ->
		    ok;
		{error, Reason} ->
		    io:format("Got an error: ~p~n", [Reason])
	    end;
	false ->
	    Key = list_to_binary("key"++integer_to_list(Acc)),
	    Obj = riakc_obj:new(<<"GeoCheckin">>, Key, Data),
	    ok  = riakc_pb_socket:put(C, Obj)
    end,
    putDataModTimeBede(C, Bucket, N, Acc+1, Incr, Ts, UserId, Amount).

%------------------------------------------------------------
% Utility functions for simulating Bede data
%------------------------------------------------------------

getBedeType(Acc, Prob) ->
    case Acc rem 2 of
	0 ->
	    <<"STAKE">>;
	_ ->
	    Rand = random:uniform(100)*1.0-1.0,
	    getType(Rand, Prob)
    end.

getType(Rand, Prob) when Rand < Prob ->
    <<"WIN">>;
getType(_Rand, _Prob) ->
    <<"LOSS">>.

getBedeStake(Acc, Stake) ->
    case Acc rem 2 of
	0 ->
	    random:uniform(100)*1.0;
	_ ->
	    Stake
    end.

%------------------------------------------------------------
% Cluster setup only.  Returns the client connection
%------------------------------------------------------------

setup_cluster(ClusterType, TestType, DDL, Data) ->
    [Node | _] = timeseries_util:build_cluster(ClusterType),
    
    case TestType of
	normal ->
	    io:format("1 - Create and activate the bucket~n"),
	    {ok, _} = timeseries_util:create_bucket(Node, DDL, 3),
	    {ok, _} = timeseries_util:activate_bucket(Node, DDL);
	n_val_one ->
	    io:format("1 - Create and activate the bucket~n"),
	    {ok, _} = timeseries_util:create_bucket(Node, DDL, 1),
	    {ok, _} = timeseries_util:activate_bucket(Node, DDL);
	no_ddl ->
	    io:format("1 - NOT Creating or activating bucket - failure test~n"),
	    ok
    end,
    Bucket = list_to_binary(timeseries_util:get_bucket()),
    C = rt:pbc(Node),
    ok = riakc_ts:put(C, Bucket, Data),
    C.

%------------------------------------------------------------
% Runs a query, and checks that the result is non-trivial (ie, returns
% > 0 records) AND matches the expected.  This protects against bad
% tests that have no expected matches
%------------------------------------------------------------

confirm_pass(C, Qry, Expected) ->
    io:format("3 - Now run the query ~p~n", [Qry]),
    Got = riakc_ts:query(C, Qry), 
    io:format("Got is ~p~n", [Got]),
    {_Cols, Records} = Got,
    N = length(Records),
    ?assertEqual(Expected, Got),
    ?assert(N > 0),
    pass.

%------------------------------------------------------------
% Runs a query, and checks that the result is an error
%------------------------------------------------------------

confirm_error(C, Qry, _Expected) ->
    io:format("3 - Now run the query ~p~n", [Qry]),
    Got = riakc_ts:query(C, Qry), 
    io:format("Got is ~p~n", [Got]),
    {Status, _Reason} = Got,
    ?assertEqual(Status, error),
    pass.

get_data(api) ->
        [[<<"family1">>, <<"seriesX">>, 100, 1, <<"test1">>, 1.0, true]] ++
	[[<<"family1">>, <<"seriesX">>, 200, 2, <<"test2">>, 2.0, false]] ++
	[[<<"family1">>, <<"seriesX">>, 300, 3, <<"test3">>, 3.0, true]] ++
	[[<<"family1">>, <<"seriesX">>, 400, 4, <<"test4">>, 4.0, false]].

%------------------------------------------------------------
% Create DDL for a table where Time is in the Ind location
%------------------------------------------------------------

get_ddl(Ind) when is_integer(Ind) ->
    L = ["CREATE TABLE Gen" ++ integer_to_list(Ind) ++" (",
	 "myfamily    varchar     not null, ",
	 "myseries    varchar     not null, ",
	 "myfloat     double      not null, ",
	 "mybool      boolean     not null, ",
	 "myint       sint64      not null, ",
	 "mybin       varchar     not null, ",
	 "PRIMARY KEY ((myfamily, myseries, quantum(time, 15, 'm')), ",
	 "myfamily, myseries, time, mybin))"],
    list_to_binary(lists:sublist(L,Ind) ++ "time timestamp not null, " ++ lists:nthtail(Ind,L));
    
get_ddl(bede) ->
    _SQL = "CREATE TABLE Bede (" ++
	"UserId varchar not null, " ++
	"UtcTime timestamp not null, " ++
	"BedeReference varchar not null, " ++
	"Category varchar not null, " ++
	"Currency varchar, " ++
	"EventDescription varchar, " ++
	"EventType sint64, " ++
	"Amount double, " ++
	"Description varchar, " ++
	"Id sint64, " ++
	"IsNew boolean, " ++
	"Status sint64, " ++
	"Type varchar not null, " ++
	"RemoteReference varchar, " ++
	"SiteCode varchar not null, " ++
	"EventStatus sint64 not null, " ++
	"TotalCredit double, " ++
	"TotalDebit double, " ++
	"VoidedAtUtc timestamp, " ++
	"PRIMARY KEY ((UserId),  UserId, UtcTime))";

get_ddl(api) ->
    _SQL = "CREATE TABLE GeoCheckin (" ++
	"myfamily    varchar     not null, " ++
	"myseries    varchar     not null, " ++
	"time        timestamp   not null, " ++
	"myint       sint64      not null, " ++
	"mybin       varchar     not null, " ++
	"myfloat     double      not null, " ++
	"mybool      boolean     not null, " ++
	"PRIMARY KEY ((myfamily, myseries, quantum(time, 15, 'm')), " ++
	"myfamily, myseries, time))";

get_ddl(api_fo) ->
    _SQL = "CREATE TABLE GeoCheckin (" ++
	"myfamily    varchar     not null, " ++
	"myseries    varchar     not null, " ++
	"time        timestamp   not null, " ++
	"myint       sint64      not null, " ++
	"mybin       varchar     not null, " ++
	"myfloat     double      not null, " ++
	"mybool      boolean     not null, " ++
	"PRIMARY KEY ((myfamily,  quantum(time, 15, 'm'), myseries), " ++
	"myfamily, time, myseries))";

get_ddl(api_tf) ->
    _SQL = "CREATE TABLE GeoCheckin (" ++
	"myfamily    varchar     not null, " ++
	"myseries    varchar     not null, " ++
	"time        timestamp   not null, " ++
	"myint       sint64      not null, " ++
	"mybin       varchar     not null, " ++
	"myfloat     double      not null, " ++
	"mybool      boolean     not null, " ++
	"PRIMARY KEY ((myfamily, myseries, quantum(time, 15, 'm')), " ++
	"myfamily, myseries))";

get_ddl(api_tl) ->
    _SQL = "CREATE TABLE GeoCheckin (" ++
	"myfamily    varchar     not null, " ++
	"myseries    varchar     not null, " ++
	"time        timestamp   not null, " ++
	"myint       sint64      not null, " ++
	"mybin       varchar     not null, " ++
	"myfloat     double      not null, " ++
	"mybool      boolean     not null, " ++
	"PRIMARY KEY ((myfamily, myseries, quantum(time, 15, 'm')), " ++
	"myfamily, myseries, time, myint))";

get_ddl(api_mf) ->
    _SQL = "CREATE TABLE GeoCheckin (" ++
	"myseries    varchar     not null, " ++
	"time        timestamp   not null, " ++
	"myint       sint64      not null, " ++
	"mybin       varchar     not null, " ++
	"myfloat     double      not null, " ++
	"mybool      boolean     not null, " ++
	"PRIMARY KEY ((myfamily, myseries, quantum(time, 15, 'm')), " ++
	"myfamily, myseries, time))";

get_ddl(api_nn) ->
    _SQL = "CREATE TABLE GeoCheckin (" ++
	"myfamily    varchar, " ++
	"myseries    varchar     not null, " ++
	"time        timestamp   not null, " ++
	"myint       sint64      not null, " ++
	"mybin       varchar     not null, " ++
	"myfloat     double      not null, " ++
	"mybool      boolean     not null, " ++
	"PRIMARY KEY ((myfamily, myseries, quantum(time, 15, 'm')), " ++
	"myfamily, myseries, time))".

get_map(api) ->
    [{<<"myfamily">>, 1},
     {<<"myseries">>, 2},
     {<<"time">>,     3},
     {<<"myint">>,    4},
     {<<"mybin">>,    5},
     {<<"myfloat">>,  6},
     {<<"mybool">>,   7}].

get_cols(api) ->
    [<<"myfamily">>,
     <<"myseries">>,
     <<"time">>,
     <<"myint">>,
     <<"mybin">>,
     <<"myfloat">>,
     <<"mybool">>].
		       
%------------------------------------------------------------
% Utility to build a list
%------------------------------------------------------------

buildList(Acc, Next) ->
    case Acc of 
	[] ->
	    [Next];
	_ ->
	    Acc ++ [Next]
    end.

%------------------------------------------------------------
% Given a list of lists, return a list of tuples
%------------------------------------------------------------

ltot(Lists) ->
    lists:foldl(fun(Entry, Acc) ->
			buildList(Acc, list_to_tuple(Entry))
		end, [], Lists).

%------------------------------------------------------------
% Return a list of indices corresponding to the passed list of field
% names
%------------------------------------------------------------

indexOf(Type, FieldNames) ->
    Fields = get_map(Type),
    lists:foldl(fun(Name, Acc) ->
			{_Name, Index} = lists:keyfind(Name, 1, Fields),
			buildList(Acc, Index)
		end, [], FieldNames).

%------------------------------------------------------------
% Return a list of values corresponding to the requested field names
%------------------------------------------------------------

valuesOf(Type, FieldNames, Record) ->
    Indices = indexOf(Type, FieldNames),
    lists:foldl(fun(Index, Acc) ->
			buildList(Acc, lists:nth(Index, Record))
		end, [], Indices).

%------------------------------------------------------------
% Return all records matching the eval function
%------------------------------------------------------------

recordsMatching(Type, Data, FieldNames, CompVals, CompFun) ->
    ltot(lists:foldl(fun(Record, Acc) ->
			     Vals = valuesOf(Type, FieldNames, Record),
			     case CompFun(Vals, CompVals) of
				 true ->
				     buildList(Acc, Record);
				 false ->
				     Acc
			     end
		     end, [], Data)).

%------------------------------------------------------------
% Return the expected data from a query
%------------------------------------------------------------

expected(Type, Data, Fields, CompVals, CompFn) ->
    Records = recordsMatching(Type, Data, Fields, CompVals, CompFn),
    case Records of
	[] ->
	    {[],[]};
	_ ->
	    {get_cols(Type), Records}
    end.

%------------------------------------------------------------
% Construct a base-SQL query
%------------------------------------------------------------

baseQry() ->
    "SELECT * FROM GeoCheckin "
        "WHERE time >= 100 AND time <= 400 "
        "AND myfamily = 'family1' "
        "AND myseries = 'seriesX' ".

getQry({NameAtom, float, OpAtom, Val}) ->		     
    baseQry() ++ "AND " ++ atom_to_list(NameAtom) ++ " " ++ atom_to_list(OpAtom) ++ " " ++ float_to_list(Val);
getQry({NameAtom, int, OpAtom, Val}) ->		     
    baseQry() ++ "AND " ++ atom_to_list(NameAtom) ++ " " ++ atom_to_list(OpAtom) ++ " " ++ integer_to_list(Val);
getQry({NameAtom, varchar, OpAtom, Val}) ->		     
    baseQry() ++ "AND " ++ atom_to_list(NameAtom) ++ " " ++ atom_to_list(OpAtom) ++ " '" ++ atom_to_list(Val) ++ "'";
getQry({NameAtom, boolean, OpAtom, Val}) ->		     
    baseQry() ++ "AND " ++ atom_to_list(NameAtom) ++ " " ++ atom_to_list(OpAtom) ++ " " ++ atom_to_list(Val).

%------------------------------------------------------------
% Template for checking that a query passes
%------------------------------------------------------------

confirm_Pass(C, {NameAtom, TypeAtom, OpAtom, Val}) ->
    confirm_Template(C, {NameAtom, TypeAtom, OpAtom, Val}, pass).

%------------------------------------------------------------
% Template for checking that a query returns an error
%------------------------------------------------------------

confirm_Error(C, {NameAtom, TypeAtom, OpAtom, Val}) ->
    confirm_Template(C, {NameAtom, TypeAtom, OpAtom, Val}, error).

%------------------------------------------------------------
% Template for single-key range queries.  For example
%
%    confirm_Template(C, {myint, int, '>', 1}, pass)
%
% adds a query clause "AND myint > 1" to the base query SQL, and
% checks that the test passes. (passing 'error' as the Result atom
% would check that the test returns an error)
%------------------------------------------------------------

confirm_Template(C, {NameAtom, TypeAtom, OpAtom, Val}, Result) ->
    Data = get_data(api),
    Qry = list_to_binary(ts_api_util:getQry({NameAtom, TypeAtom, OpAtom, Val})),
    Fields   = [<<"time">>, <<"myfamily">>, <<"myseries">>] ++ [list_to_binary(atom_to_list(NameAtom))],
    case TypeAtom of
	varchar ->
	    CompVals = [<<"family1">>,  <<"seriesX">>] ++ [list_to_binary(atom_to_list(Val))];
	_ ->
	    CompVals = [<<"family1">>,  <<"seriesX">>] ++ [Val]
    end,
    case OpAtom of
	'>' ->
	    CompFn = fun(Vals, Cvals) ->
			     [T,V1,V2,V3] = Vals,
			     [C1,C2,C3] = Cvals,
			     (T >= 100) and (T =< 400) and (V1 == C1) and (V2 == C2) and (V3 > C3)
		     end;
	'>=' ->
	    CompFn = fun(Vals, Cvals) ->
			     [T,V1,V2,V3] = Vals,
			     [C1,C2,C3] = Cvals,
			     (T >= 100) and (T =< 400) and (V1 == C1) and (V2 == C2) and (V3 >= C3)
		     end;
	'<' ->
    	    CompFn = fun(Vals, Cvals) ->
			     [T,V1,V2,V3] = Vals,
			     [C1,C2,C3] = Cvals,
			     (T >= 100) and (T =< 400) and (V1 == C1) and (V2 == C2) and (V3 < C3)
		     end;
	'=<' ->
	    CompFn = fun(Vals, Cvals) ->
			     [T,V1,V2,V3] = Vals,
			     [C1,C2,C3] = Cvals,
			     (T >= 100) and (T =< 400) and (V1 == C1) and (V2 == C2) and (V3 =< C3)
		     end;
	'<=' ->
	    CompFn = fun(Vals, Cvals) ->
			     [T,V1,V2,V3] = Vals,
			     [C1,C2,C3] = Cvals,
			     (T >= 100) and (T =< 400) and (V1 == C1) and (V2 == C2) and (V3 =< C3)
		     end;
	'=' ->
	    CompFn = fun(Vals, Cvals) ->
			     [T,V1,V2,V3] = Vals,
			     [C1,C2,C3] = Cvals,
			     (T >= 100) and (T =< 400) and (V1 == C1) and (V2 == C2) and (V3 == C3)
		     end;
	'!=' ->
	    CompFn = fun(Vals, Cvals) ->
			     [T,V1,V2,V3] = Vals,
			     [C1,C2,C3] = Cvals,
			     (T >= 100) and (T =< 400) and (V1 == C1) and (V2 == C2) and (V3 /= C3)
		     end
    end,
    Expected = expected(api, Data, Fields, CompVals, CompFn),
    case Result of
	pass ->
	    confirm_pass(C, Qry, Expected);
	error ->
	    confirm_error(C, Qry, Expected)
    end.

%------------------------------------------------------------
% Check function to return what confirm_Template would do
%------------------------------------------------------------

check_Template({NameAtom, TypeAtom, OpAtom, Val}) ->
    Data = get_data(api),
    Qry = ts_api_util:getQry({NameAtom, TypeAtom, OpAtom, Val}),
    Fields   = [<<"time">>, <<"myfamily">>, <<"myseries">>] ++ [list_to_binary(atom_to_list(NameAtom))],
    case TypeAtom of
	varchar ->
	    CompVals = [<<"family1">>,  <<"seriesX">>] ++ [list_to_binary(atom_to_list(Val))];
	_ ->
	    CompVals = [<<"family1">>,  <<"seriesX">>] ++ [Val]
    end,
    case OpAtom of
	'>' ->
	    CompFn = fun(Vals, Cvals) ->
			     [T,V1,V2,V3] = Vals,
			     [C1,C2,C3] = Cvals,
			     (T >= 100) and (T =< 400) and (V1 == C1) and (V2 == C2) and (V3 > C3)
		     end;
	'>=' ->
	    CompFn = fun(Vals, Cvals) ->
			     [T,V1,V2,V3] = Vals,
			     [C1,C2,C3] = Cvals,
			     (T >= 100) and (T =< 400) and (V1 == C1) and (V2 == C2) and (V3 >= C3)
		     end;
	'<' ->
    	    CompFn = fun(Vals, Cvals) ->
			     [T,V1,V2,V3] = Vals,
			     [C1,C2,C3] = Cvals,
			     (T >= 100) and (T =< 400) and (V1 == C1) and (V2 == C2) and (V3 < C3)
		     end;
	'=<' ->
	    CompFn = fun(Vals, Cvals) ->
			     [T,V1,V2,V3] = Vals,
			     [C1,C2,C3] = Cvals,
			     (T >= 100) and (T =< 400) and (V1 == C1) and (V2 == C2) and (V3 =< C3)
		     end;
	'=' ->
	    CompFn = fun(Vals, Cvals) ->
			     [T,V1,V2,V3] = Vals,
			     [C1,C2,C3] = Cvals,
			     (T >= 100) and (T =< 400) and (V1 == C1) and (V2 == C2) and (V3 == C3)
		     end;
	'!=' ->
	    CompFn = fun(Vals, Cvals) ->
			     [T,V1,V2,V3] = Vals,
			     [C1,C2,C3] = Cvals,
			     (T >= 100) and (T =< 400) and (V1 == C1) and (V2 == C2) and (V3 /= C3)
		     end
    end,
    Expected = expected(api, Data, Fields, CompVals, CompFn),
    {Qry, Fields, CompVals, Expected}.


