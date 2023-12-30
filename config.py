profile = 'dev8'
region= 'us-west-2'
event = {'customerName': 'arosenfeld85'}
sfn = 'sfnDefinition.json'

mocks = {
    "MockOutput": {"mock": True}
}

resources = {
    "FeatureFlag": "arn:aws:lambda:us-west-2:884056075937:function:bc-infrastructure-feature-flags-rosi",
    "MyCode": "my_code.debug_func"
}
