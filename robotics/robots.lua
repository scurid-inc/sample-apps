-- On top of the file, defined as global
t = 0
tmax = 0

function dump(o)
    if type(o) == 'table' then
       local s = '{ '
       for k,v in pairs(o) do
          if type(k) ~= 'number' then k = '"'..k..'"' end
          s = s .. '['..k..'] = ' .. dump(v) .. ','
       end
       return s .. '} '
    else
       return tostring(o)
    end
 end
function init()
    robot.colored_blob_omnidirectional_camera.enable()
    tmax = 100
    t = math.floor( math.random(0,tmax) )
end

function driveAsCar(forwardSpeed, angularSpeed)

    -- We have an equal component, and an opposed one   
    leftSpeed  = forwardSpeed - angularSpeed
    rightSpeed = forwardSpeed + angularSpeed
  
    robot.wheels.set_velocity(leftSpeed,rightSpeed)
end

function step()
    log(robot.positioning.position.x, robot.positioning.position.y)
    sensingLeft = robot.proximity[3].value + robot.proximity[4].value +
                robot.proximity[5].value + robot.proximity[6].value

    sensingRight = robot.proximity[22].value+ robot.proximity[21].value +
                robot.proximity[20].value + robot.proximity[19].value

    if( sensingLeft ~= 0 ) then
    driveAsCar(7,-3)
    elseif( sensingRight ~= 0 ) then
    driveAsCar(7,3)
    else
    driveAsCar(10,0)
    end

    --Blinking

    t = t + 1

    if(t<tmax) then
        t = t + 1
        robot.leds.set_single_color(13,"black")
    else
        t = 0
        robot.leds.set_single_color(13,"red")
    end
end

function destroy()
end

