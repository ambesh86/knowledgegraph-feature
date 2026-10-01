resource "aws_volume_attachment" "eugene_data_volume_attachment" {
  device_name = "/dev/sdb"
  volume_id   = aws_ebs_volume.eugene_data_volume.id
  instance_id = aws_instance.eugene_database_instance.id
}