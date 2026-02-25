import datetime
import time
import utils_rs485

serial_rs485 = utils_rs485.init_rs485_communication()  
time.sleep(1)

now = datetime.datetime.now(datetime.timezone.utc)
now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")



serial_get_wind_comm = '0R1'
serial_get_composite_comm = '0R0'
serial_get_combined_comm = '0R'

utils_rs485.write_command(serial_rs485, serial_get_composite_comm)

response = utils_rs485.read_response(serial_rs485)
response = response.replace('\r\n','')
response = response.replace('\n','')
response = response.replace('\r','')


print(response)

# expected response

#   (venv) root@Gateway:/data_inactive/test2 python3 test_wtx536.py
#   0R1,Dn=159D,Dm=159D,Dx=159D,Sn=0.0M,Sm=0.0M,Sx=0.0M0R2,Ta=22.7C,Ua=39.8P,Pa=987.7H0R3,Rc=0.05M,Rd=40s,Ri=0.0M,Hc=0.0M,Hd=0s,Hi=0.0M0R5,Th=23.7C,Vh=0.0N,Vs=5.2V,Vr=3.596V

# #xplanation of the response format:
# #wind sensor data
# 1 = Dn Direction minimum 	
# 1 = Dm Direction average
# 1 = Dx Direction maximum
# 1 = Sn Speed minimum
# 1 = Sm Speed average
# 1 = Sx Speed maximum
# 0 = Reserved
# 0 = Reserved [& = Delimiter]
# 0 = Dn Direction minimum
# 1 = Dm Direction average
# 0 = Dx Direction maximum
# 0 = Sn Speed minimum
# 1 = Sm Speed average
# 0 = Sx Speed maximum
# 0 = Reserved
# 0 = Reserved
# #air sensor data
# 1 = Pa Air pressure 	
# 1 = Ta Air temperature
# 1 = Th Heating temperature 	
# 1 = Pa Air pressure 	
# 0 = Tp internal temperature
# 1 = Ua Air humidity
# 0 = Reserved
# 0 = Reserved
# 0 = Reserved
# 0 = Reserved [& = Delimiter]
# 1 = Pa Air pressure
# 1 = Ta Air temperature
# 0 = Tp internal temperature
# 1 = Ua Air humidity
# 0 = Reserved
# 0 = Reserved
# 0 = Reserved
# 0 = Reserved

# #rain/hail sensor data
# 1 = Rc Rain amount 	Format:1111110010000000
# 1 = Rd Rain duration
# 1 = Ri Rain intensity
# 1 = Hc Hail amount
# 1 = Hd Hail duration
# 1 = Hi Hail intensity
# 1 = Rp Rain peak
# 1 = Rp Hail peak [& = Delimiter]
# 1 = Rc Rain amount
# 1 = Rd Rain duration
# 1 = Ri Rain intensity
# 1 = Hc Hail amount
# 1 = Hd Hail duration
# 1 = Hi Hail intensity
# 1 = Rp Rain peak
# 1 = Rp Hail peak

# #sensor status data
# 1 = Th Heating temperature 	Format:1111000011000000
# 1 = Vh Heating voltage
# 1 = Vs Supply voltage
# 1 = Vr 3.5 V reference voltage
# 1 = Id Information field

