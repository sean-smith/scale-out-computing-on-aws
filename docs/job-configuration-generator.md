---
title: Job Submission Generator
---
<script src="https://code.angularjs.org/1.7.9/angular.js"></script>



!!!configuration "We are here to help"
    This page will generate the `qsub` command based on the parameter you will specify for your job.

# Your Job Parameters:

<body ng-app="myApp">
<div ng-controller="myCtrl">


  
<input size="35" style="border: 2px solid black;height: 30px;font-size: 15px" type="text" ng-change="myFunc()" ng-model="instance_ami" placeholder="Specify your instance AMI" />
<input size="35" style="border: 2px solid black;height: 30px;font-size: 15px" type="text" ng-change="myFunc()" ng-model="instance_type" placeholder="Specify your instance type" />
<br><br>
<input size="35" style="border: 2px solid black;height: 30px;font-size: 15px" type="text" ng-change="myFunc()" ng-model="subnet_id" placeholder="Selection a subnet id" />
<input size="35" style="border: 2px solid black;height: 30px;font-size: 15px" type="text" ng-change="myFunc()" ng-model="spot_price" placeholder="Your maximum spot price" />
<br><br>
<input size="35" style="border: 2px solid black;height: 30px;font-size: 15px" type="text" ng-change="myFunc()" ng-model="root_size" placeholder="Size of the root partition (in GB)" />
<input size="35" style="border: 2px solid black;height: 30px;font-size: 15px" type="text" ng-change="myFunc()" ng-model="scratch_size" placeholder="Size of the scratch partition (in GB)" />
<br><br>
<input size="50" style="border: 2px solid black;height: 30px;font-size: 15px" type="text" ng-change="myFunc()" ng-model="scratch_size_iops" placeholder="IOPS to be provisioned for scratch partition" />
<br><br>
// to add FSX <br>
<input type="checkbox" ng-change="myFunc()" ng-model="efa_support"> I want to use EFA<br>
<input type="checkbox" ng-change="myFunc()" ng-model="placement_group"> I want to use Placement Group<br>
  
  
<h1>Your Job Submission Command</h1>
<strong>user@host:</strong> qsub {{qsub_instance_ami}} 
{{qsub_instance_type}} 
{{qsub_subnet_id}} 
{{qsub_spot_price}}
{{qsub_efa_support}}
{{qsub_placement_group}}
{{qsub_root_size}}
{{qsub_scratch_size}}
{{qsub_scratch_size_iops}}
</div>

<script>
  angular.module('myApp', [])
    .controller('myCtrl', ['$scope', function($scope) {
      $scope.count = 0;
      $scope.myFunc = function() {
        
        if($scope.instance_ami){$scope.qsub_instance_ami = "-l instance_ami=" + $scope.instance_ami;}else{$scope.qsub_instance_ami = "";}
        if($scope.instance_type){$scope.qsub_instance_type = "-l instance_type=" + $scope.instance_type;}else{$scope.qsub_instance_type = "";}
        if($scope.subnet_id){$scope.qsub_subnet_id = "-l subnet_id=" + $scope.subnet_id;}else{$scope.qsub_subnet_id = "";}
        if($scope.spot_price){$scope.qsub_spot_price = "-l spot_price=" + $scope.spot_price;}else{$scope.qsub_spot_price= "";}
        if($scope.root_size){$scope.qsub_root_size= "-l root_size=" + $scope.root_size;}else{$scope.qsub_root_size= "";}
        if($scope.scratch_size){$scope.qsub_scratch_size = "-l scratch_size=" + $scope.scratch_size;}else{$scope.qsub_scratch_size= "";}
        if($scope.scratch_size_iops){$scope.qsub_scratch_size_iops= "-l scratch_size_iops=" + $scope.scratch_size_iops;}else{$scope.qsub_scratch_size_iops= "";}

        
        if($scope.efa_support){$scope.qsub_efa_support = "-l efa_support=True";}else{$scope.qsub_efa_support= "";}
        if($scope.placement_group){$scope.qsub_placement_group = "-l placement_group=True";}else{$scope.qsub_placement_group= "";}

       


      };
    }]);
</script>
</body>

