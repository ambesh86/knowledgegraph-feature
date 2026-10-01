    resource "aws_iam_role" "cloudwatch_events_ecs_role" {
      name_prefix = "cloudwatch-events-ecs-role-"
      assume_role_policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
          {
            Action    = "sts:AssumeRole"
            Effect    = "Allow"
            Principal = {
              Service = "events.amazonaws.com"
            }
          }
        ]
      })
    }

    resource "aws_iam_role_policy" "cloudwatch_events_ecs_policy" {
      name   = "cloudwatch-events-ecs-policy"
      role   = aws_iam_role.cloudwatch_events_ecs_role.id
      policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
          {
            Action = [
              "ecs:RunTask",
              "iam:PassRole"
            ]
            Effect   = "Allow"
            Resource = "*" # Restrict this to specific resources if possible
          }
        ]
      })
    }