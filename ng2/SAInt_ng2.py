# Dummy federate of gas network  - SAInt tool

import helics as h
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)


def destroy_federate(fed):
    grantedtime = h.helicsFederateRequestTime(fed, h.HELICS_TIME_MAXTIME)
    status = h.helicsFederateDisconnect(fed)
    h.helicsFederateFree(fed)
    h.helicsCloseLibrary()
    logger.info("Federate finalized")


# Calculating the electrical output from the thermal power input iteratively
def CalculatePMW (Y, X0):
    iter = 0
    while iter < 20:       
        delY = Y*3.6 - (HR0*X_new + HR1*X_new*X0 + HR2*X_new*X_new*X_new) # = Pthermal/3.6
        if abs(delY) > 0.0001:
            delY_delX = -(HR0 + 2*HR1*X0 + 3*HR2*X0*X0)
            X_new = X0 - delY/delY_delX
            X0 = X_new
            iter+=1
        else: break         
    return X_new


if __name__ == "__main__":
    
    ##########  Registering  federate and configuring from JSON #############
    
    fed = h.helicsCreateValueFederateFromConfig("SAInt_ng2_Config.json")
    federate_name = h.helicsFederateGetName(fed)
    logger.info(f"Created federate {federate_name}")

    sub_count = h.helicsFederateGetInputCount(fed)
    logger.debug(f"\tNumber of subscriptions: {sub_count}")
    pub_count = h.helicsFederateGetPublicationCount(fed)
    logger.debug(f"\tNumber of publications: {pub_count}")

    ##############  Entering Execution Mode  ##################################
    h.helicsFederateEnterExecutingMode(fed)
    logger.info("Entered HELICS execution mode")

    
    update_interval = int(h.helicsFederateGetTimeProperty(fed, h.HELICS_PROPERTY_TIME_PERIOD))
    grantedtime = 0
    total_interval = 1
    # Heat rate coefficients
    HR0 = 20           # MJ/kWh
    HR1 = -0.075       # (MJ/kWh)/MW 
    HR2 = 0.001        # (MJ/kWh)/(MW*MW)
    GCV = 39           # MJ/m^3
    QMin = 0           # m^3/s
    QMax = 1000        # m^3/s
    
    # As long as granted time is in the time range to be simulated...
    while grantedtime < total_interval:

        # Time request for the next physical interval to be simulated
        requested_time = grantedtime + update_interval
        logger.debug(f"Requesting time {requested_time}")
        grantedtime = h.helicsFederateRequestTime(fed, requested_time)
        logger.debug(f"Granted time {grantedtime}")

        ############# From/To Transmission Node 2 ##################################

        # Get the power output of the node 2 in MW
        P_MW2 = h.helicsInputGetDouble(("node.2.requested"))
        logger.debug(f"\tReceived P_MW {P_MW2:.2f}" f" from input Transmission Node 2")
        #P_MW = P_MMBtu*0.29307107

        # Calculate the heat rate and gas off take
        HR2 = HR0 + HR1*P_MW2 + HR2*P_MW2*P_MW2
        Pthermal2 = HR2*P_MW2/3.6   # 3.6 is a MJ/kWh to MJ/MWh conversion factor
        QSET2 = Pthermal2/GCV

        logger.debug(f"\tQSET requested from transmission Node 2 (m^3/s): {QSET2:.2f}")

        # Check for QSET limits
        if QSET2 > QMax:
            QSET2 = QMax
        elif QSET2 < QMin:
            QSET2 = QMin
        logger.debug(f"\tQSET available for transmission Node 2 (m^3/s): {QSET2:.2f}")

        Pthermal2 = GCV*QSET2
        P_MW2_new = CalculatePMW (Pthermal2, P_MW2)
        #P_MMBtu_new = P_MW_new/0.29307107

        h.helicsPublicationPublishDouble("node.2.avail", P_MW2_new)
        logger.debug(f"\tElectrical output power available for Node 2 " f"{P_MW2_new:.2f}")

############# From/To Transmission Node 3 ##################################

        # Get the power output of the node 2 in MW
        P_MW3 = h.helicsInputGetDouble(("node.3.requested"))
        logger.debug(f"\tReceived P_MW {P_MW3:.2f}" f" from input Transmission Node 3")
        #P_MW = P_MMBtu*0.29307107

        # Calculate the heat rate and gas off take
        HR3 = HR0 + HR1*P_MW3 + HR2*P_MW3*P_MW3
        Pthermal3 = HR3*P_MW3/3.6   # 3.6 is a MJ/kWh to MJ/MWh conversion factor
        QSET3 = HR3*P_MW3/GCV

        logger.debug(f"\tQSET requested from transmission Node 3 (m^3/s): {QSET3:.2f}")

        # Check for QSET limits
        if QSET3 > QMax:
            QSET3 = QMax
        elif QSET3 < QMin:
            QSET3 = QMin
        logger.debug(f"\tQSET available for transmission Node 3 (m^3/s): {QSET3:.2f}")

        Pthermal3 = GCV*QSET3
        P_MW3_new = CalculatePMW (Pthermal3, P_MW3)
        #P_MMBtu_new = P_MW_new/0.29307107

        h.helicsPublicationPublishDouble("node.3.avail", P_MW3_new)
        logger.debug(f"\tElectrical output power available for Node 3 " f"{P_MW3_new}")


    # Cleaning up HELICS stuff once we've finished the co-simulation.
    destroy_federate(fed)
    
