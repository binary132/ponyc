use "collections"
use "options"
use "time"

actor Main
  let _env: Env
  var _logtable: U64 = 20
  var _iterate: U64 = 10000
  var _chunk: U64 = 1024
  var _streamer_count: U64 = 4
  var _updater_count: U64 = 8
  var _updates: U64 = 0
  var _to: Array[Updater] val
  var _start: U64

  new create(env: Env) =>
    _env = env
    _to = recover Array[Updater] end
    _start = Time.nanos()

    try
      arguments()

      var size = (1 << _logtable) / _updater_count
      _updates = _chunk * _iterate * _streamer_count

      let count = _updater_count

      _to = recover
        var updaters = Array[Updater](count)

        for i in Range(0, count) do
          updaters.push(Updater(i, size))
        end

        consume updaters
      end

      for i in Range(0, _streamer_count) do
        Streamer(this, _to, size, _chunk, _chunk * _iterate * i)(_iterate)
      end
    end

  be streamer_done() =>
    if (_streamer_count = _streamer_count - 1) == 1 then
      for u in _to.values() do
        u.done(this)
      end
    end

  be updater_done() =>
    if (_updater_count = _updater_count - 1) == 1 then
      var elapsed = (Time.nanos() - _start).f64()
      var gups = _updates.f64() / elapsed
      _env.out.print(
        "Time: " + (elapsed / 1e9).string() + " GUPS: " + gups.string()
        )
    end

  fun ref arguments() ? =>
    var options = Options(_env)

    options
      .add("logtable", "l", None, I64Argument)
      .add("iterate", "i", None, I64Argument)
      .add("chunk", "c", None, I64Argument)
      .add("streamers", "s", None, I64Argument)
      .add("updaters", "u", None, I64Argument)

    for option in options do
      match option
      | ("logtable", var arg: I64) => _logtable = arg.u64()
      | ("iterate", var arg: I64) => _iterate = arg.u64()
      | ("chunk", var arg: I64) => _chunk = arg.u64()
      | ("streamers", var arg: I64) => _streamer_count = arg.u64()
      | ("updaters", var arg: I64) => _updater_count = arg.u64()
      | ParseError => usage() ; error
      end
    end

  fun ref usage() =>
    _env.out.print(
      """
      gups_basic [OPTIONS]
        --logtable  N   log2 of the total table size. Defaults to 20.
        --iterate   N   number of iterations. Defaults to 10000.
        --chunk     N   chunk size. Defaults to 1024.
        --streamers N   number of streamers. Defaults to 4.
        --updaters  N   number of updaters. Defaults to 8.
      """
      )

actor Streamer
  let main: Main
  let updaters: Array[Updater] val
  let shift: U64
  let mask: U64
  let chunk: U64
  let rand: PolyRand

  new create(main': Main, updaters': Array[Updater] val, size: U64, chunk': U64,
    seed: U64) =>
    main = main'
    updaters = updaters'
    shift = size.bitwidth() - size.clz()
    mask = updaters.size() - 1
    chunk = chunk'
    rand = PolyRand(seed)

  be apply(iterate: U64) =>
    let upts = updaters.size()
    let chks = chunk

    var list = recover Array[Array[U64] iso](upts) end

    for i in Range(0, upts) do
      list.push(recover Array[U64](chks) end)
    end

    try
      for i in Range(0, chks) do
        var datum = rand()
        var updater = (datum >> shift) and mask
        list(updater).push(datum)
      end

      var vlist: Array[Array[U64] iso] val = consume list

      for i in vlist.keys() do
        var data = vlist(i)

        if data.size() > 0 then
          updaters(i)(data)
        end
      end
    end

    if iterate > 0 then
      apply(iterate - 1)
    else
      main.streamer_done()
    end

actor Updater
  var table: Array[U64] ref

  new create(index: U64, size: U64) =>
    table = Array[U64](size)

    var offset = index * size

    for i in Range(0, size) do
      table.push(i + offset)
    end

  be apply(data: Array[U64] val) =>
    try
      for datum in data.values() do
        var i = datum and (table.size() - 1)
        table(i) = table(i) xor datum
      end
    end

  be done(main: Main) => main.updater_done()

class PolyRand
  let poly: U64
  let period: U64
  var last: U64

  new create(seed: U64) =>
    poly = 7
    period = 1317624576693539401
    last = 1
    _seed(seed)

  fun ref apply(): U64 =>
    last = (last << 1) xor
      if (last and (1 << 63)) != 0 then poly else 0 end

  fun ref _seed(seed: U64) =>
    var n = seed % period

    if n == 0 then
      last = 1
    else
      var m2 = Array[U64](64)
      last = 1

      for i in Range(0, 63) do
        m2.push(last)
        apply()
        apply()
      end

      var i: U64 = 64 - n.clz()
      last = 2

      while i > 0 do
        var temp: U64 = 0

        for j in Range(0, 64) do
          if ((last >> j) and 1) != 0 then
            try temp = temp xor m2(j) end
          end
        end

        last = temp
        i = i - 1

        if ((n >> i) and 1) != 0 then
          apply()
        end
      end
    end
