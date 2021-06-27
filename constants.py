dosage = ["DOSE 1", "DOSE 2"]
cost = ["FREE", "PAID"]       # Note: Values should be in lower case
age_limit = [18, 45]          # Supported values 18 and 45
vaccine_type = ["COVAXIN", "COVISHIELD", "SPUTNIK V"]
is_query_by_district = True   # If True, it will search by district code, otherwise by pincode
dist_code = 294               # This value will be used if is_query_by_district is set to True, Refer to `state_to_district_mapping.csv` for getting district id
pincode = "560011"            # This value will be used if is_query_by_district is set to False

skype_notifier = False        # Set to True, if you would like the notifications to be sent via Skype
recipients = [""]             # Add list of all the skype recipients to whom the notification has to be sent
# Skype credentials
user_id = ""
password = ""

