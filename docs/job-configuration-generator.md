---
title: Job Submission Generator
---
<script src="https://code.angularjs.org/1.7.9/angular.js"></script>
<script src="https://code.angularjs.org/1.7.9/angular-messages.js"></script>

!!!note "Automatic parameter selection"
    You can manually specify parameters at job submission using the command below. If needed, all parameters [can also be automatically configured at queue level](../tutorials/integration-ec2-job-parameters/#how-to-use-custom-parameters). 
    ____
    
    Job will use the default parameters configured for its queue unless the parameter is explicitely specified during submission (**job parameters override queue parameters**),
    ____
    
    [Refer to this page](../tutorials/launch-your-first-job/#examples) for examples.
    

<body ng-app="myApp">
<div ng-controller="myCtrl">

<style>
* {
  box-sizing: border-box;
}

input[type=text], select, textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  resize: vertical;
}

label {
  padding: 12px 12px 12px 0;
  display: inline-block;
}

input[type=submit] {
  background-color: #4CAF50;
  color: white;
  padding: 12px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  float: right;
}

input[type=submit]:hover {
  background-color: #45a049;
}

.container {
  border-radius: 5px;
  background-color: #f2f2f2;
  padding: 5px;
}

.col-25 {
  float: left;
  width: 25%;
  margin-top: 6px;
}

.col-75 {
  float: left;
  width: 75%;
  margin-top: 6px;
}

/* Clear floats after the columns */
.row:after {
  content: "";
  display: table;
  clear: both;
}

/* Responsive layout - when the screen is less than 600px wide, make the two columns stack on top of each other instead of next to each other */
@media screen and (max-width: 600px) {
  .col-25, .col-75, input[type=submit] {
    width: 100%;
    margin-top: 0;
  }
}
</style>






<div class="container">



<h2> Your Command </h2>
<strong>user@host:</strong> qsub {{qsub_instance_ami}} 
{{qsub_instance_type}} 
{{qsub_subnet_id}} 
{{qsub_spot_price}}
{{qsub_efa_support}}
{{qsub_placement_group}}
{{qsub_root_size}}
{{qsub_scratch_size}}
{{qsub_scratch_iops}}
{{qsub_fsx_lustre_bucket}}
{{qsub_fsx_lustre_size}}
{{qsub_fsx_lustre_dns}}
{{qsub_ht_support}}
myscript.sh

<h2> Job Parameters</h2>

<form name="QsubForm">
<h3> EC2 parameters: </h3>
   <input required name="instance_ami" size="35" ng-minlength="3" style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="instance_ami" placeholder="Specify your instance AMI" pattern="^ami-[a-zA-Z0-9]*" />
   <div ng-messages="QsubForm.instance_ami.$error">
        <div style="color: red; font-size: medium" ng-message="pattern">Image name must start with "ami-"</div>
   </div>
   
   <input size="35" style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="instance_type" placeholder="Specify your instance type (comma separated if multiples)" />
   
   <input name="subnet_id" size="35" style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="subnet_id" placeholder="Specify your subnet id" pattern="^sub-[a-zA-Z0-9]*" />
    <div ng-messages="QsubForm.subnet_id.$error">
        <div style="color: red; font-size: medium" ng-message="pattern">Subnet name must start with "sub-"</div>
   </div>
   
   <input name="spot_price" size="35" style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="spot_price" placeholder="Specify your maximum spot price (job will automatically use SPOT instances)" pattern="[-+]?[0-9]*\.?[0-9]*" />
    <div ng-messages="QsubForm.spot_price.$error">
        <div style="color: red; font-size: medium" ng-message="pattern">Spot Price must be a float (eg 1.2)</div>
   </div>

    
<h3> Storage parameters: </h3>   
   
   
   <input name="root_size" size="35"  style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="root_size" placeholder="Size of the root partition (in GB)"  pattern="\d+" />
   <div ng-messages="QsubForm.root_size.$error">
        <div style="color: red; font-size: medium" ng-message="pattern">Root Size must be a number</div>
   </div>
   
   <input name="scratch_size" size="35"  style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="scratch_size" placeholder="Size of the scratch partition (in GB)" pattern="\d+"/>
    <div ng-messages="QsubForm.scratch_size.$error">
        <div style="color: red; font-size: medium" ng-message="pattern">Scratch Size must be a number</div>
   </div>
   
  
   <input size="50" name = "scratch_iops" style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="scratch_iops" placeholder="IOPS to be provisioned for scratch partition (will automatically provision io1 EBS if specified)" pattern="\d+" />
    <div ng-messages="QsubForm.scratch_iops.$error">
        <div style="color: red; font-size: medium" ng-message="pattern">Provisioned IO/s must be a number</div>
   </div>
   
   
   <input size="35"  style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="fsx_lustre_bucket" placeholder="Specify S3 bucket name to mount using FSx for Lustre (will create a new one)" />
   <input size="35"  style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="fsx_lustre_size" placeholder="Size of the FSx partition (in GB)" />
   <input size="35"  style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="fsx_lustre_dns" placeholder="Specify an existing FSx to mount on all nodes" />

<h3>Flags: </h3>
   <input type="checkbox" ng-change="myFunc()" ng-model="efa_support"> I want to use EFA<br>
   <input type="checkbox" ng-change="myFunc()" ng-model="placement_group"> I do not want to use Placement Group (enabled by default)<br>
   <input type="checkbox" ng-change="myFunc()" ng-model="ht_support"> I want to enable HyperThreading (disabled by default)<br>

</form> 
  

</div>

<script>
  angular.module('myApp', ['ngMessages'])
    .controller('myCtrl', ['$scope', function($scope) {
      $scope.count = 0;
      $scope.myFunc = function() {
        
        if($scope.instance_ami){$scope.qsub_instance_ami = "-l instance_ami=" + $scope.instance_ami;}else{$scope.qsub_instance_ami = "";}
        if($scope.instance_type){$scope.qsub_instance_type = "-l instance_type=" + $scope.instance_type;}else{$scope.qsub_instance_type = "";}
        if($scope.subnet_id){$scope.qsub_subnet_id = "-l subnet_id=" + $scope.subnet_id;}else{$scope.qsub_subnet_id = "";}
        if($scope.spot_price){$scope.qsub_spot_price = "-l spot_price=" + $scope.spot_price;}else{$scope.qsub_spot_price= "";}
        if($scope.root_size){$scope.qsub_root_size= "-l root_size=" + $scope.root_size;}else{$scope.qsub_root_size= "";}
        if($scope.scratch_size){$scope.qsub_scratch_size = "-l scratch_size=" + $scope.scratch_size;}else{$scope.qsub_scratch_size= "";}
        if($scope.scratch_iops){$scope.qsub_scratch_iops= "-l scratch_iops=" + $scope.scratch_iops;}else{$scope.qsub_scratch_iops= "";}     
        if($scope.efa_support){$scope.qsub_efa_support = "-l efa_support=True";}else{$scope.qsub_efa_support= "";}
        if($scope.placement_group){$scope.qsub_placement_group = "-l placement_group=False";}else{$scope.qsub_placement_group= "";}
        if($scope.ht_support){$scope.qsub_ht_support = "-l ht_support=True";}else{$scope.qsub_ht_support= "";}

        
        if($scope.fsx_lustre_bucket){$scope.qsub_fsx_lustre_bucket = "-l fsx_lustre_bucket=" + $scope.fsx_lustre_bucket;}else{$scope.qsub_fsx_lustre_bucket = "";}
        if($scope.fsx_lustre_size){$scope.qsub_fsx_lustre_size = "-l fsx_lustre_size=" + $scope.fsx_lustre_size;}else{$scope.qsub_fsx_lustre_size = "";}
        if($scope.fsx_lustre_dns){$scope.qsub_fsx_lustre_dns = "-l fsx_lustre_dnst=" + $scope.fsx_lustre_dns;}else{$scope.qsub_fsx_lustre_dns = "";}

      
      };
    }]);
</script>




</body>

