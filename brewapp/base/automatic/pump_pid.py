import time
from automaticlogic import *
from brewapp import app, socketio
import pprint

class PID(object):
    ek_1 = 0.0
    xk_1 = 0.0
    xk_2 = 0.0

    yk = 0.0

    GMA_HLIM = 100.0
    GMA_LLIM = 0.0

    def __init__(self, ts, kc, ti, td):
        self.kc = kc
        self.ti = ti
        self.td = td
        self.ts = ts
        self.k0 = 0.0
        self.k1 = 0.0
        self.pp = 0.0
        self.pi = 0.0
        self.pd = 0.0

        if (self.ti == 0.0):
            self.k0 = 0.0
        else:
            self.k0 = self.kc * self.ts / self.ti
        self.k1 = self.kc * self.td / self.ts

    def calc(self, xk, tset):

        ek = 0.0
        ek = tset - xk  # calculate e[k] = SP[k] - PV[k]

        # y[k] = y[k-1] + Kc*(PV[k-1] - PV[k])
        self.pp = self.kc * (PID.xk_1 - xk)
        self.pi = self.k0 * ek  # + Kc*Ts/Ti * e[k]
        self.pd = self.k1 * (2.0 * PID.xk_1 - xk - PID.xk_2)
        PID.yk += self.pp + self.pi + self.pd

        PID.xk_2 = PID.xk_1  # PV[k-2] = PV[k-1]
        PID.xk_1 = xk    # PV[k-1] = PV[k]

        # limit y[k] to GMA_HLIM and GMA_LLIM
        if (PID.yk > PID.GMA_HLIM):
            PID.yk = PID.GMA_HLIM
        if (PID.yk < PID.GMA_LLIM):
            PID.yk = PID.GMA_LLIM

        return PID.yk


@brewautomatic()
class PumpPIDLogic(Automatic):

    configparameter = [
      {"name": "wait_time", "value":5},
      {"name": "P", "value": 44},
      {"name": "I", "value": 165},
      {"name": "D", "value": 4},
      {"name": "PumpWait", "value": 4}
    ]

    def run(self):
        sampleTime = 5

        agitatorName = int(app.brewapp_kettle_state[self.kid]["agitator"])

        p = float(self.config["P"])
        i = float(self.config["I"])
        d = float(self.config["D"])
        pumpWait = float(self.config["PumpWait"])
	wait_time = float(self.config["wait_time"])

        pid = PID(wait_time, p, i, d)

        while self.isRunning():
            heat_percent = pid.calc(self.getCurrentTemp(), self.getTargetTemp())
            heating_time = sampleTime * heat_percent / 100
            wait_time = sampleTime - heating_time

            print 'PID Controller: {} %, heating: {} waiting: {}'.format(heat_percent, heating_time, wait_time)
            # Check if we need heating
            if(heating_time > 0.1):
                # If not already running, start pump and wait 1 round (5 Seconds)
                if(app.brewapp_switch_state[agitatorName] == False):
                    switchOn(agitatorName)
                    socketio.sleep(sampleTime)
                    continue
                else:
  	            # Pump running, lets heat 
                    self.switchHeaterON()

            # Sleepy time
            socketio.sleep(heating_time)
            # Check if we need to switch off Heating (only if we need more than 100ms of sleep)
            if(wait_time > 0.1):
               self.switchHeaterOFF()

            # Sleepy time
            socketio.sleep(wait_time)
