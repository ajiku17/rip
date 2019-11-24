"""
Your awesome Distance Vector router for CS 168
"""

import sim.api as api
import sim.basics as basics


# We define infinity as a distance of 16.
INFINITY = 16


class DVRouter (basics.DVRouterBase):
  #NO_LOG = True # Set to True on an instance to disable its logging
  POISON_MODE = True # Can override POISON_MODE here
  DEFAULT_TIMER_INTERVAL = 5 # Can override this yourself for testing

  def __init__ (self):
    """
    Called when the instance is initialized.

    You probably want to do some additional initialization here.
    """
    self.start_timer() # Starts calling handle_timer() at correct rate

    # self.activePorts = {} # { portN: latency }

    self.neighboursDistanceVector = {} # { neighbouringPort : [latency, {destination : distance}] }
    self.distanceVector = {} # { destination : [distance, neighbourPort] }

  def handle_link_up (self, port, latency):
    """
    Called by the framework when a link attached to this Entity goes up.

    The port attached to the link and the link latency are passed in.
    """
    self.neighboursDistanceVector[port] = [latency, {}]
    self.recalculateDistanceVector()
    # print '%s: port %d is up!, latency: %d' % (api.get_name(self), port, latency)

  def handle_link_down (self, port):
    """
    Called by the framework when a link attached to this Entity does down.

    The port number used by the link is passed in.
    """

    updated = False

    del self.neighboursDistanceVector[port]

    for destination in self.distanceVector.keys():
      if self.distanceVector[destination][1] == port:
        updated = True
        self.removeRoute(destination)

    self.recalculateDistanceVector()

    # print '%s: port %d is down!' % (api.get_name(self), port)

  def handle_rx (self, packet, port):
    """
    Called by the framework when this Entity receives a packet.

    packet is a Packet (or subclass).
    port is the port number it arrived on.

    You definitely want to fill this in.
    """
    updatedEntries = {}
    #self.log("RX %s on %s (%s)", packet, port, api.current_time())
    if isinstance(packet, basics.RoutePacket):

      if self.POISON_MODE and packet.latency >= INFINITY:
        if packet.destination in self.distanceVector and self.distanceVector[packet.destination][1] == port:
          "We have to change routes, but for now let's just forget them"
          del self.neighboursDistanceVector[port][1][packet.destination]
          self.removeRoute(packet.destination)
      else:
        self.neighboursDistanceVector[port][1][packet.destination] = packet.latency
        updatedEntries = self.recalculateDistanceVector()

    elif isinstance(packet, basics.HostDiscoveryPacket):
      self.neighboursDistanceVector[port][1] = {packet.src : 0}
      updatedEntries = self.recalculateDistanceVector()
    else:
      if packet.dst in self.distanceVector and self.distanceVector[packet.dst][1] != port and self.distanceVector[packet.dst][1] < INFINITY:
        self.send(packet, self.distanceVector[packet.dst][1])

    # notify neighbours that we have updated routes available
    self.sendTable(updatedEntries)


  def handle_timer (self):
    """
    Called periodically.

    When called, your router should send tables to neighbors.  It also might
    not be a bad place to check for whether any entries have expired.
    """
    self.expireRoutes()
    self.sendTable()

  def recalculateDistanceVector(self, debug=False):
    updatedEntries = {}
    for n in self.neighboursDistanceVector.keys():
      cost, dv = self.neighboursDistanceVector[n]
      for destination in dv.keys():
        distance = dv[destination]
        currentEstimate = INFINITY if destination not in self.distanceVector else self.distanceVector[destination][0]
        if cost + distance < currentEstimate:
          self.distanceVector[destination] = [cost + distance, n, api.current_time()]
          updatedEntries[destination] = cost + distance, n
        elif cost + distance == currentEstimate: # update the timer
          self.distanceVector[destination][2] = api.current_time()

    return updatedEntries

  def sendTable(self, updatedEntries=None):
    entries = updatedEntries if updatedEntries != None else self.distanceVector
    for route in entries.keys():
      routePacket = basics.RoutePacket(route, entries[route][0])
      port=entries[route][1]
      self.send(routePacket, port=port, flood=True)

  def expireRoutes(self):
    for route in self.distanceVector.keys():
      if self.neighboursDistanceVector[self.distanceVector[route][1]][1][route] != 0 and api.current_time() - self.distanceVector[route][2] > 15:
        # notify neighbours HERE!
        del self.neighboursDistanceVector[self.distanceVector[route][1]][1][route]
        self.removeRoute(route)
        

  def removeRoute(self, destination):
    if self.POISON_MODE:
      poisonRoute = basics.RoutePacket(destination, INFINITY)
      self.send(poisonRoute, flood=True)
    
    del self.distanceVector[destination]