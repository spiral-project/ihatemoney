local items = redis.call('lrange', KEYS[1], 0, tonumber(ARGV[2]))
local expiry = tonumber(ARGV[1])
local a = 0
local oldest = nil

for idx=1,#items do
    if tonumber(items[idx]) >= expiry then
        a = a + 1

        if oldest == nil then
            oldest = tonumber(items[idx])
        end
    else
        break
    end
end

return {oldest, a}
