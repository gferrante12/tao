// Do NOT change. Changes will be lost next time file is generated

#define R__DICTIONARY_FILENAME dItmpdIbdIjunodOihepdOacdOcndIel9_amd64_gcc11dIReleasedIJ25dO7dO1dItaoswdIbuilddIDataModeldIRecEventdIsrcdITvtVertexRecEvtDict
#define R__NO_DEPRECATION

/*******************************************************************/
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#define G__DICTIONARY
#include "ROOT/RConfig.hxx"
#include "TClass.h"
#include "TDictAttributeMap.h"
#include "TInterpreter.h"
#include "TROOT.h"
#include "TBuffer.h"
#include "TMemberInspector.h"
#include "TInterpreter.h"
#include "TVirtualMutex.h"
#include "TError.h"

#ifndef G__ROOT
#define G__ROOT
#endif

#include "RtypesImp.h"
#include "TIsAProxy.h"
#include "TFileMergeInfo.h"
#include <algorithm>
#include "TCollectionProxyInfo.h"
/*******************************************************************/

#include "TDataMember.h"

// Header files passed as explicit arguments
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RecEvent/Event/TvtVertexRecEvt.h"

// Header files passed via #pragma extra_include

// The generated code does not explicitly qualify STL entities
namespace std {} using namespace std;

namespace ROOT {
   static void *new_TaocLcLTvtVertexRecEvt(void *p = nullptr);
   static void *newArray_TaocLcLTvtVertexRecEvt(Long_t size, void *p);
   static void delete_TaocLcLTvtVertexRecEvt(void *p);
   static void deleteArray_TaocLcLTvtVertexRecEvt(void *p);
   static void destruct_TaocLcLTvtVertexRecEvt(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const ::Tao::TvtVertexRecEvt*)
   {
      ::Tao::TvtVertexRecEvt *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TInstrumentedIsAProxy< ::Tao::TvtVertexRecEvt >(nullptr);
      static ::ROOT::TGenericClassInfo 
         instance("Tao::TvtVertexRecEvt", ::Tao::TvtVertexRecEvt::Class_Version(), "Event/TvtVertexRecEvt.h", 37,
                  typeid(::Tao::TvtVertexRecEvt), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &::Tao::TvtVertexRecEvt::Dictionary, isa_proxy, 4,
                  sizeof(::Tao::TvtVertexRecEvt) );
      instance.SetNew(&new_TaocLcLTvtVertexRecEvt);
      instance.SetNewArray(&newArray_TaocLcLTvtVertexRecEvt);
      instance.SetDelete(&delete_TaocLcLTvtVertexRecEvt);
      instance.SetDeleteArray(&deleteArray_TaocLcLTvtVertexRecEvt);
      instance.SetDestructor(&destruct_TaocLcLTvtVertexRecEvt);
      return &instance;
   }
   TGenericClassInfo *GenerateInitInstance(const ::Tao::TvtVertexRecEvt*)
   {
      return GenerateInitInstanceLocal(static_cast<::Tao::TvtVertexRecEvt*>(nullptr));
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const ::Tao::TvtVertexRecEvt*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));
} // end of namespace ROOT

namespace Tao {
//______________________________________________________________________________
atomic_TClass_ptr TvtVertexRecEvt::fgIsA(nullptr);  // static to hold class pointer

//______________________________________________________________________________
const char *TvtVertexRecEvt::Class_Name()
{
   return "Tao::TvtVertexRecEvt";
}

//______________________________________________________________________________
const char *TvtVertexRecEvt::ImplFileName()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::TvtVertexRecEvt*)nullptr)->GetImplFileName();
}

//______________________________________________________________________________
int TvtVertexRecEvt::ImplFileLine()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::TvtVertexRecEvt*)nullptr)->GetImplFileLine();
}

//______________________________________________________________________________
TClass *TvtVertexRecEvt::Dictionary()
{
   fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::TvtVertexRecEvt*)nullptr)->GetClass();
   return fgIsA;
}

//______________________________________________________________________________
TClass *TvtVertexRecEvt::Class()
{
   if (!fgIsA.load()) { R__LOCKGUARD(gInterpreterMutex); fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::TvtVertexRecEvt*)nullptr)->GetClass(); }
   return fgIsA;
}

} // namespace Tao
namespace Tao {
//______________________________________________________________________________
void TvtVertexRecEvt::Streamer(TBuffer &R__b)
{
   // Stream an object of class Tao::TvtVertexRecEvt.

   if (R__b.IsReading()) {
      R__b.ReadClassBuffer(Tao::TvtVertexRecEvt::Class(),this);
   } else {
      R__b.WriteClassBuffer(Tao::TvtVertexRecEvt::Class(),this);
   }
}

} // namespace Tao
namespace ROOT {
   // Wrappers around operator new
   static void *new_TaocLcLTvtVertexRecEvt(void *p) {
      return  p ? new(p) ::Tao::TvtVertexRecEvt : new ::Tao::TvtVertexRecEvt;
   }
   static void *newArray_TaocLcLTvtVertexRecEvt(Long_t nElements, void *p) {
      return p ? new(p) ::Tao::TvtVertexRecEvt[nElements] : new ::Tao::TvtVertexRecEvt[nElements];
   }
   // Wrapper around operator delete
   static void delete_TaocLcLTvtVertexRecEvt(void *p) {
      delete (static_cast<::Tao::TvtVertexRecEvt*>(p));
   }
   static void deleteArray_TaocLcLTvtVertexRecEvt(void *p) {
      delete [] (static_cast<::Tao::TvtVertexRecEvt*>(p));
   }
   static void destruct_TaocLcLTvtVertexRecEvt(void *p) {
      typedef ::Tao::TvtVertexRecEvt current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class ::Tao::TvtVertexRecEvt

namespace ROOT {
   static TClass *vectorlEdoublegR_Dictionary();
   static void vectorlEdoublegR_TClassManip(TClass*);
   static void *new_vectorlEdoublegR(void *p = nullptr);
   static void *newArray_vectorlEdoublegR(Long_t size, void *p);
   static void delete_vectorlEdoublegR(void *p);
   static void deleteArray_vectorlEdoublegR(void *p);
   static void destruct_vectorlEdoublegR(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const vector<double>*)
   {
      vector<double> *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TIsAProxy(typeid(vector<double>));
      static ::ROOT::TGenericClassInfo 
         instance("vector<double>", -2, "vector", 389,
                  typeid(vector<double>), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &vectorlEdoublegR_Dictionary, isa_proxy, 0,
                  sizeof(vector<double>) );
      instance.SetNew(&new_vectorlEdoublegR);
      instance.SetNewArray(&newArray_vectorlEdoublegR);
      instance.SetDelete(&delete_vectorlEdoublegR);
      instance.SetDeleteArray(&deleteArray_vectorlEdoublegR);
      instance.SetDestructor(&destruct_vectorlEdoublegR);
      instance.AdoptCollectionProxyInfo(TCollectionProxyInfo::Generate(TCollectionProxyInfo::Pushback< vector<double> >()));

      instance.AdoptAlternate(::ROOT::AddClassAlternate("vector<double>","std::vector<double, std::allocator<double> >"));
      return &instance;
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const vector<double>*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));

   // Dictionary for non-ClassDef classes
   static TClass *vectorlEdoublegR_Dictionary() {
      TClass* theClass =::ROOT::GenerateInitInstanceLocal(static_cast<const vector<double>*>(nullptr))->GetClass();
      vectorlEdoublegR_TClassManip(theClass);
   return theClass;
   }

   static void vectorlEdoublegR_TClassManip(TClass* ){
   }

} // end of namespace ROOT

namespace ROOT {
   // Wrappers around operator new
   static void *new_vectorlEdoublegR(void *p) {
      return  p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<double> : new vector<double>;
   }
   static void *newArray_vectorlEdoublegR(Long_t nElements, void *p) {
      return p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<double>[nElements] : new vector<double>[nElements];
   }
   // Wrapper around operator delete
   static void delete_vectorlEdoublegR(void *p) {
      delete (static_cast<vector<double>*>(p));
   }
   static void deleteArray_vectorlEdoublegR(void *p) {
      delete [] (static_cast<vector<double>*>(p));
   }
   static void destruct_vectorlEdoublegR(void *p) {
      typedef vector<double> current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class vector<double>

namespace {
  void TriggerDictionaryInitialization_TvtVertexRecEvtDict_Impl() {
    static const char* headers[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RecEvent/Event/TvtVertexRecEvt.h",
nullptr
    };
    static const char* includePaths[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Python/3.11.10/include/python3.11",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Boost/1.85.0",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/log4cpp/1.1.3/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/ROOT/6.30.08/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J24.2.0/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Geant4/10.04.p02.juno/include/geant4",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/HepMC/2.06.11/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/genie/3.04.02/include/GENIE",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/frontier/2.10.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-c/6.1.9/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-cpp/1.1.12/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libyaml/0.2.4/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime/core/session",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/nuwro/21.09.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RecEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RecEvent/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/RecEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.4.0/ExternalLibs/ROOT/6.30.08/include/",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/RecEvent/",
nullptr
    };
    static const char* fwdDeclCode = R"DICTFWDDCLS(
#line 1 "TvtVertexRecEvtDict dictionary forward declarations' payload"
#pragma clang diagnostic ignored "-Wkeyword-compat"
#pragma clang diagnostic ignored "-Wignored-attributes"
#pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
extern int __Cling_AutoLoading_Map;
namespace Tao{class __attribute__((annotate("$clingAutoload$/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RecEvent/Event/TvtVertexRecEvt.h")))  TvtVertexRecEvt;}
)DICTFWDDCLS";
    static const char* payloadCode = R"DICTPAYLOAD(
#line 1 "TvtVertexRecEvtDict dictionary payload"


#define _BACKWARD_BACKWARD_WARNING_H
// Inline headers
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RecEvent/Event/TvtVertexRecEvt.h"

#undef  _BACKWARD_BACKWARD_WARNING_H
)DICTPAYLOAD";
    static const char* classesHeaders[] = {
"Tao::TvtVertexRecEvt", payloadCode, "@",
nullptr
};
    static bool isInitialized = false;
    if (!isInitialized) {
      TROOT::RegisterModule("TvtVertexRecEvtDict",
        headers, includePaths, payloadCode, fwdDeclCode,
        TriggerDictionaryInitialization_TvtVertexRecEvtDict_Impl, {}, classesHeaders, /*hasCxxModule*/false);
      isInitialized = true;
    }
  }
  static struct DictInit {
    DictInit() {
      TriggerDictionaryInitialization_TvtVertexRecEvtDict_Impl();
    }
  } __TheDictionaryInitializer;
}
void TriggerDictionaryInitialization_TvtVertexRecEvtDict() {
  TriggerDictionaryInitialization_TvtVertexRecEvtDict_Impl();
}
