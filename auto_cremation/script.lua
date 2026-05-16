-- Cremation Transport Depot — script.lua
-- Scans all city cemeteries periodically and transports the deceased
-- to the nearest available crematorium, keeping burial grounds clear.

local CEMETERY_ID    = "$cemetery00"
local CREMATORY_ID   = "$crematory00"
local SCAN_INTERVAL  = 256   -- game ticks between transport runs
local BATCH_SIZE     = 20    -- max persons transported per cemetery per run

-- ─── Helpers ────────────────────────────────────────────────────────────────

local function manhattanDist(a, b)
    return math.abs(a:getX() - b:getX()) + math.abs(a:getY() - b:getY())
end

local function nearestBuilding(src, pool)
    local best, bestDist = nil, math.huge
    for _, b in ipairs(pool) do
        local d = manhattanDist(src, b)
        if d < bestDist then
            bestDist = d
            best = b
        end
    end
    return best
end

local function collectBuildings(draftId)
    local result = {}
    local draft = Draft.fromId(draftId)
    if not draft then return result end
    City.forEachBuilding(function(b)
        table.insert(result, b)
    end, draft)
    return result
end

-- ─── Transport logic ─────────────────────────────────────────────────────────

local function runTransport(depot)
    local crematoriums = collectBuildings(CREMATORY_ID)
    if #crematoriums == 0 then return 0 end

    local cemeteries = collectBuildings(CEMETERY_ID)
    if #cemeteries == 0 then return 0 end

    local totalMoved = 0

    for _, cemetery in ipairs(cemeteries) do
        local occupancy = cemetery:getAttribute("people") or 0
        if occupancy > 0 then
            local target = nearestBuilding(cemetery, crematoriums)
            if target then
                local moved = math.min(occupancy, BATCH_SIZE)
                cemetery:setAttribute("people", occupancy - moved)
                totalMoved = totalMoved + moved
            end
        end
    end

    return totalMoved
end

-- ─── Script callbacks ────────────────────────────────────────────────────────

local script = {}

function script:init(building)
    building:setAttribute("ticks",     0)
    building:setAttribute("total",     0)
    building:setAttribute("lastBatch", 0)
    building:setAttribute("runs",      0)
end

function script:update(building)
    local ticks = (building:getAttribute("ticks") or 0) + 1
    building:setAttribute("ticks", ticks)

    if ticks % SCAN_INTERVAL == 0 then
        local ok, moved = pcall(runTransport, building)
        if ok and moved and moved > 0 then
            local total = (building:getAttribute("total") or 0) + moved
            local runs  = (building:getAttribute("runs")  or 0) + 1
            building:setAttribute("total",     total)
            building:setAttribute("lastBatch", moved)
            building:setAttribute("runs",      runs)
        end
    end
end

function script:onClick(building)
    local total = building:getAttribute("total")     or 0
    local last  = building:getAttribute("lastBatch") or 0
    local runs  = building:getAttribute("runs")      or 0

    local cemeteries  = collectBuildings(CEMETERY_ID)
    local crematoriums = collectBuildings(CREMATORY_ID)

    local lines = {
        "=== Cremation Transport Depot ===",
        "",
        "Cemeteries monitored : " .. #cemeteries,
        "Crematoriums linked   : " .. #crematoriums,
        "",
        "Transport runs total  : " .. runs,
        "Last batch moved      : " .. last,
        "Persons moved (total) : " .. total,
        "",
        "Next scan in " .. (SCAN_INTERVAL - ((building:getAttribute("ticks") or 0) % SCAN_INTERVAL)) .. " ticks.",
    }

    if #crematoriums == 0 then
        table.insert(lines, "")
        table.insert(lines, "WARNING: No crematorium found.")
        table.insert(lines, "Build a crematorium to activate transport.")
    end

    Script.showInfoDialog(table.concat(lines, "\n"))
end

return script
