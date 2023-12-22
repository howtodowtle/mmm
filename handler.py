import all_538


def lambda_handler(event, context):
    print("Received event:", event)
    print("Received context:", context)
    return all_538.main()
