local keys = redis.call('keys', KEYS[1])
local res = 0

for i=1,#keys,5000 do
    res = res + redis.call(
        'del', unpack(keys, i, math.min(i+4999, #keys))
    )
end

return res
