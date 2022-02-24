class SmartBoardAPIURL:
    OK_CODES = [200, 201]
    SMART_BOARD_URL_ENDPOINT = 'https://app.smartboard.solar'
    SMART_BOARD_SANDBOX_URL_ENDPOINT = 'https://dev.smartboard.solar'

    READ_LEAD_URL = '/apis/get_lead_data?lead_id='
    READ_IMAGE_URL = '/apis/get_lead_images?lead_id='
