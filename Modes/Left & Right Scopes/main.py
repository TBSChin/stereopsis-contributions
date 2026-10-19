import os
import pygame


#Knob1 - left scope x position
#Knob2 - right scope x position
#Knob3 - line width
#Knob4 - foreground color
#Knob5 - background color

def setup(screen, eyesy) :
    global xr, yr
    xr = eyesy.xres
    yr = eyesy.yres

def draw(screen, eyesy) :
    global xr, yr

    eyesy.color_picker_bg(eyesy.knob5)

    w100 = (yr*0.045) #max line width

    #first scope - LEFT
    for i in range (0,50) :
        x0 = int(eyesy.knob1*(xr*0.5)) 
        x1 = x0 + (eyesy.audio_in[i] / 35)
        y = i * (yr/48)
        color = eyesy.color_picker_lfo(eyesy.knob4)
        
        pygame.draw.line(screen, color, [x0, y], [x1, y], int(eyesy.knob3*w100+1))
        
    #second scope - RIGHT (uses: eyesy.audio_in_r[])
    for i in range (0,50) :
        x0 = int((eyesy.knob2*(xr*0.5))+(xr*0.5)) 
        x1 = x0 + (eyesy.audio_in_r[i] /35)
        y = i * (yr/48)
        color = eyesy.color_picker_lfo(eyesy.knob4)
        
        pygame.draw.line(screen, color, [x0, y], [x1, y], int(eyesy.knob3*w100+1))
