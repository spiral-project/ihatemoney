local current
local amount = tonumber(ARGV[2])
current = redis.call("incrby", KEYS[1], amount)

if tonumber(current) == amount then
    redis.call("expire", KEYS[1], ARGV[1])
end

return current
