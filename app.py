#!/usr/bin/env python3

from aws_cdk import core

from ecs_elk.ecs_elk_stack import EcsElkStack


app = core.App()
EcsElkStack(app, "ecs-elk")

app.synth()
